#include "dump.h"
#include "frontend/frontend.h"
#include "game_code.h"
#include "kernel/kernel.h"
#include "loader.h"
#include "log.h"
#include "memory.h"
#include "platform.h"
#include "save_storage.h"
#include "video/internal.h"

#include <SDL3/SDL.h>
#include <windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <array>
#include <cstdio>
#include <filesystem>
#include <string_view>

namespace game_code {
const RecompEntry *functions() { return recomp_functions; }
size_t function_count() { return recomp_function_count; }
}

namespace {
constexpr uint64_t europe_title = 0x000400000007AF00;
constexpr std::array<uint8_t, 32> expected_code = {
    0x59, 0x60, 0x68, 0xed, 0xc3, 0x50, 0x8a, 0xa8, 0x82, 0x2c, 0xc3, 0x89, 0x46, 0x1b, 0x58, 0x5d,
    0x53, 0x08, 0x75, 0xb0, 0x2a, 0x66, 0x07, 0x0f, 0xc0, 0xaf, 0x25, 0xfe, 0x88, 0xe9, 0x8c, 0x94,
};

GameImage load(const char *path) {
    if (peek_program_id(path) != europe_title)
        fatal("Expected a decrypted New Super Mario Bros. 2 European image (CTR-P-ABEP): %s", path);
    open_dump(path);
    const auto &code = dump().code();
    if (code.size() != 0x503000) fatal("Unexpected cartridge code size");
    std::array<uint8_t, 32> hash{};
    const auto status = BCryptHash(BCRYPT_SHA256_ALG_HANDLE, nullptr, 0, const_cast<PUCHAR>(code.data()),
                                   static_cast<ULONG>(code.size()), hash.data(), static_cast<ULONG>(hash.size()));
    if (status < 0 || hash != expected_code) fatal("The cartridge code does not match this build");
    mem::init();
    return load_game();
}

int verify_native_startup(const char *path) {
    const auto image = load(path);
    constexpr uint32_t address = 0x00100024;
    const auto *first = game_code::functions();
    const auto *end = first + game_code::function_count();
    const auto *entry = std::lower_bound(first, end, address,
        [](const RecompEntry &item, uint32_t target) { return item.addr < target; });
    if (entry == end || entry->addr != address) fatal("The original BSS initialization routine is missing");
    const uint32_t start = image.data_end;
    const uint32_t size = image.bss_size;
    std::fill_n(mem::ptr(start), size, uint8_t{0xa5});
    *mem::ptr(start - 1) = 0x4b;
    *mem::ptr(start + size) = 0x37;
    Ctx state{};
    entry->fn(&state);
    const bool cleared = std::all_of(mem::ptr(start), mem::ptr(start) + size,
                                     [](uint8_t byte) { return byte == 0; });
    if (!cleared || state.r[0] != start + size || state.r[1] != start + size ||
        *mem::ptr(start - 1) != 0x4b || *mem::ptr(start + size) != 0x37)
        fatal("The recompiled BSS initialization routine produced incorrect results");
    std::printf("Native ARM routine at 0x%08x cleared %u bytes and preserved its boundaries\n", address, size);
    return 0;
}

int verify_texture_updates() {
    constexpr uint32_t width = 32, height = 24;
    std::array<uint8_t, width * height> compressed{};
    uint32_t seed = 0x9b31a59u;
    for (auto &byte : compressed) {
        seed = seed * 1664525u + 1013904223u;
        byte = uint8_t(seed >> 24);
    }
    pica::Texture texture{};
    texture.data = compressed.data();
    texture.bytes = static_cast<uint32_t>(compressed.size());
    texture.width = width;
    texture.height = height;
    texture.format = 13; // ETC1 with 4-bit alpha
    texture.mag_linear = false;
    texture.wrap_s = texture.wrap_t = 0;
    std::array<uint8_t, width * height * 4> reference{}, incremental{};
    pica::decode_texture(texture, incremental.data());
    for (uint32_t y = 0; y < height; ++y) {
        for (uint32_t x = 0; x < width; ++x) {
            const auto sample = pica::sample_texture(texture, (x + 0.5f) / width, (height - y - 0.5f) / height);
            const auto *pixel = incremental.data() + (y * width + x) * 4;
            if (pixel[0] != sample.r || pixel[1] != sample.g || pixel[2] != sample.b || pixel[3] != sample.a)
                fatal("ETC1A4 full decode differs from texture sampling at %u,%u", x, y);
        }
    }

    auto previous = compressed;
    for (const size_t offset : {size_t{0}, size_t{8}, size_t{21}, compressed.size() - 1}) {
        compressed[offset] ^= 0x7b;
        pica::update_etc1a4(texture, previous.data(), incremental.data());
        pica::decode_texture(texture, reference.data());
        if (incremental != reference || previous != compressed)
            fatal("ETC1A4 block cache differs from full decode after changing byte %zu", offset);
    }
    std::puts("ETC1A4 full decode and incremental updates match texture sampling and reference decoding");
    return 0;
}

void play(const char *path) {
    const auto image = load(path);
    nsmb2::lock_save_directory(platform::state_dir());
    kernel::init(image);
    kernel::run(image);
}
}

int main(int argc, char **argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--verify-textures") return verify_texture_updates();
    const bool verify = argc == 3 && std::string_view(argv[1]) == "--verify-startup";
    if ((argc > 2 && !verify) || (argc == 2 && std::string_view(argv[1]) == "--help")) {
        std::puts("NewSuperMarioBros2 [path to decrypted NSMB2-EUR.cxi]");
        return argc > 2 ? 2 : 0;
    }
    log_cfg::init();
    if (verify) return verify_native_startup(argv[2]);
    const char *base = SDL_GetBasePath();
    const auto directory = std::filesystem::path(base ? base : ".");
    auto image = directory / "NSMB2-EUR.cxi";
    if (!std::filesystem::is_regular_file(image)) image = directory / ".." / "extracted" / "NSMB2-EUR.cxi";
    const auto path = argc == 2 ? std::string(argv[1]) : image.string();
    if (!std::filesystem::is_regular_file(path)) fatal("Cartridge image not found: %s", path.c_str());
    frontend::run(play, path.c_str());
}



