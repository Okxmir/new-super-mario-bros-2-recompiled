"""Build the title-specific frontend from the pinned Clockwork runtime."""

import argparse
import shutil
from pathlib import Path


def between(source, start, end):
    left = source.index(start)
    return source[left:source.index(end, left)]


def edit(path, transform):
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def frontend(source):
    source = source.replace('#include "handoff.h"\n', '').replace('#include "launcher.h"\n', '')
    source = source.replace(between(source, "bool hand_off_or_explain", "void run(void (*start)"), "")
    source = source.replace("const char *cli_dump, bool force_launcher, bool play", "const char *cli_dump")
    source = source.replace(
        '        if (std::string problem; !hand_off_or_explain(cli_dump, &problem)) fatal("%s", problem.c_str());\n',
        "",
    )
    source = source.replace(between(source, "    // the launcher, unless", "    if (device && !pica::gpu::init"),
                            '    game_path = s.game_path;\n    const std::string game_id = "nsmb2";\n')
    source = source.replace('SDL_SetAppMetadata("Clockwork", nullptr, "io.github.yw2recomp")',
                            'SDL_SetAppMetadata("New Super Mario Bros. 2", nullptr, "local.nsmb2.native")')
    source = source.replace('"Clockwork - Yo-kai Watch 2"', '"New Super Mario Bros. 2"')
    source = source.replace('"Clockwork: Yo-kai Watch 2 stopped"', '"New Super Mario Bros. 2"')
    source = source.replace("    fatal_hook = show_fatal;",
                            '    if (!std::getenv("NSMB2_NO_DIALOG")) fatal_hook = show_fatal;')
    return source


def platform(source):
    source = source.replace('#include "log.h"', '#include "log.h"\n#include <SDL3/SDL.h>')
    return source.replace(
        between(source, "        std::filesystem::path base;", "        std::filesystem::create_directories(d);"),
        '''        const char *override_path = std::getenv("NSMB2_DATA_DIR");
        const char *base = SDL_GetBasePath();
        if ((!override_path || !*override_path) && !base) fatal("could not find the executable directory");
        auto d = override_path && *override_path ? std::filesystem::path(override_path)
                                                 : std::filesystem::path(base) / "userdata";
''',
    ).replace('"YW2_STATE_DIR"', '"NSMB2_SAVE_DIR"')


def filesystem(source):
    source = source.replace("    bool romfs = false, update = false;",
                            "    bool romfs = false, update = false, read_only = false;")
    source = source.replace("            if (romfs) {\n                req.reply(1, 0, ERR_UNSUPPORTED);",
                            "            if (romfs || read_only) {\n                req.reply(1, 0, ERR_UNSUPPORTED);")
    source = source.replace("            if (!romfs) {\n                host.flush();",
                            """            if (romfs || read_only) {
                req.reply(1, 0, ERR_UNSUPPORTED);
                break;
            }
            {
                host.flush();""")
    source = source.replace("        case SELF_NCCH:\n        case NCCH:",
                            """        case NCCH: {
            uint64_t title = 0;
            if (path.data.size() >= sizeof title) std::memcpy(&title, path.data.data(), sizeof title);
            if (title == 0x0004009b00010202ull) {
                const char *base = SDL_GetBasePath();
                auto image = std::filesystem::path(base ? base : ".") / "mii.romfs";
                if (!fs::is_regular_file(image)) {
                    LOG("fs: missing Mii resource archive %s; rerun the build command", image.string().c_str());
                    return ERR_ARCHIVE_NOT_FOUND;
                }
                *out = {id, image};
                return kernel::RESULT_OK;
            }
            if (title != dump().program_id()) return ERR_ARCHIVE_NOT_FOUND;
            *out = {id, {}};
            return kernel::RESULT_OK;
        }
        case SELF_NCCH:""")
    source = source.replace("        auto f = std::make_shared<File>();\n        if (a.root.empty()) {",
                            """        auto f = std::make_shared<File>();
        if (a.id == NCCH && !a.root.empty()) {
            if (flags != 1 || path.type != PATH_BINARY || path.data.size() != 20 ||
                std::any_of(path.data.begin(), path.data.end(), [](uint8_t b) { return b != 0; }))
                return ERR_FILE_NOT_FOUND;
            f->host_path = a.root;
            f->host.open(a.root, std::ios::binary | std::ios::in);
            if (!f->host) return ERR_FILE_NOT_FOUND;
            f->read_only = true;
            *out = f;
            return kernel::RESULT_OK;
        }
        if (a.root.empty()) {""")
    source = source.replace("    std::fstream host;",
                            "    std::fstream host;\n    const std::vector<uint8_t> *exefs = nullptr;")
    source = source.replace("        return fs::file_size(host_path);",
                            "        return exefs ? exefs->size() : fs::file_size(host_path);")
    source = source.replace("            } else {\n                host.clear();\n                host.seekg",
                            """            } else if (exefs) {
                got = offset >= exefs->size() ? 0 : std::min<uint64_t>(len, exefs->size() - offset);
                if (got) std::memcpy(mem::ptr(dest), exefs->data() + offset, size_t(got));
            } else {
                host.clear();
                host.seekg""")
    source = source.replace("            if (type == 5 && !dump().has_update())",
                            """            if (type == 2 && a.id == SELF_NCCH && flags == 1 &&
                path.type == PATH_BINARY && path.data.size() == 12) {
                const char *name = reinterpret_cast<const char *>(path.data.data() + 4);
                auto entry = dump().exefs_files().find(std::string(name, strnlen(name, 8)));
                if (entry == dump().exefs_files().end()) return ERR_FILE_NOT_FOUND;
                f->exefs = &entry->second;
                f->read_only = true;
                *out = f;
                return kernel::RESULT_OK;
            }
            if (type == 5 && !dump().has_update())""")
    source = source.replace('#include "platform.h"', '#include "platform.h"\n#include "save_storage.h"')
    source = source.replace("            if (req.arg(0) == SAVE_DATA && !fs::exists(save_root())) {",
                            """            if (req.arg(0) == SAVE_DATA) {
                const auto format = nsmb2::read_save_format(save_root());
                if (format) {
                    auto reply = req.reply(5, 0);
                    for (uint32_t field : *format) reply.push(field);
                    break;
                }
            }
            if (req.arg(0) == SAVE_DATA && !fs::exists(save_root())) {""")
    source = source.replace(
        between(source, "            if (req.arg(0) == SAVE_DATA) {\n                std::error_code ec;",
                "            req.reply(1, 0);\n            break;\n        default:"),
        """            if (req.arg(0) == SAVE_DATA) {
                nsmb2::format_save(save_root(), {req.arg(3) * 512, req.arg(4), req.arg(5), req.arg(8) & 1});
            }
""")
    source = source.replace("                d->entries.push_back({e.path().filename().string(), e.is_directory(ec), e.is_directory(ec) ? 0 : e.file_size(ec)});",
                            """                if (!nsmb2::is_save_format_file(e.path()))
                    d->entries.push_back({e.path().filename().string(), e.is_directory(ec), e.is_directory(ec) ? 0 : e.file_size(ec)});""")
    return source.replace('#include "service.h"', '#include "service.h"\n#include <SDL3/SDL.h>')

def gpu(source):
    source = source.replace('#include "shaders.inc"', '#include "shaders.inc"\n#include "nsmb2_lcd.inc"')
    source = source.replace("SPIRV_blit_lcd_frag, sizeof SPIRV_blit_lcd_frag", "nsmb2_lcd, sizeof nsmb2_lcd")
    source = source.replace("    if (in_h == 400) { // a top-screen frame is done",
                            """    // Mario's RGB565 buffers have 256 rows per column. The top
    // LCD starts 16 columns into a 416-column framebuffer.
    const bool top = in_w == 256 && in_h == 416 && out_w == 256 && out_h == 416 && flags == 0x2200;
    const bool bottom = in_w == 256 && in_h == 416 && out_w == 256 && out_h == 320 && flags == 0x2204;
    if (top) { // a top-screen transfer""")
    source = source.replace("    bool top = in_h == 400;\n", "")
    source = source.replace("    bool to_lcd = !(flags & 2) && !(flags & 0x20) && (((flags >> 12) & 7) <= 1);",
                            "    const bool to_lcd = top || bottom;")
    source = source.replace("    int w = int(src->th >> vs), h = int(src->tw >> hs); // upright: rows of the output become columns\n    (void)out_w, (void)out_h;",
                            """    const int scale = int(src->th / in_h);
    const int w = (top ? 400 : 320) * scale, h = 240 * scale;
    const uint32_t lcd_address = out + (top ? 16 * 256 * 2 : 0);""")
    source = source.replace("    LcdFrames &f = lcd[out];", "    LcdFrames &f = lcd[lcd_address];")
    source = source.replace("    lcd.erase(addr); // an LCD buffer written by the CPU shows that, not an older GPU frame",
                            """    for (auto &[address, frame] : lcd) {
        const uint32_t lcd_start = to_physical(address);
        const uint32_t span = 400 * 256 * 2;
        if (p < uint64_t(lcd_start) + span && lcd_start < uint64_t(p) + size)
            frame.latest = -1;
    }""")
    # A native-resolution target can be downloaded without an intermediate GPU blit.
    source = source.replace(
        between(source, "    SDL_GPUTexture *tmp = make_texture(w, h", "    SDL_GPUTransferBufferCreateInfo tbi"),
        """    SDL_GPUTexture *image = s->tex;
    SDL_GPUCommandBuffer *cmd = SDL_AcquireGPUCommandBuffer(dev);
    if (s->tw != w || s->th != h) {
        image = make_texture(w, h, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
                             SDL_GPU_TEXTUREUSAGE_SAMPLER | SDL_GPU_TEXTUREUSAGE_COLOR_TARGET);
        SDL_GPUBlitInfo blit{};
        blit.source.texture = s->tex;
        blit.source.y = uint32_t(s->margin * s->scale);
        blit.source.w = s->tw;
        blit.source.h = h * uint32_t(s->scale);
        blit.destination.texture = image;
        blit.destination.w = w;
        blit.destination.h = h;
        blit.load_op = SDL_GPU_LOADOP_DONT_CARE;
        blit.filter = SDL_GPU_FILTER_LINEAR;
        SDL_BlitGPUTexture(cmd, &blit);
    }
""")
    source = source.replace("    src.texture = tmp, src.w = w, src.h = h, src.d = 1;",
                            "    src.texture = image, src.w = w, src.h = h, src.d = 1;")
    source = source.replace("    SDL_ReleaseGPUTexture(dev, tmp);\n    s->drawn = false;",
                            "    if (image != s->tex) SDL_ReleaseGPUTexture(dev, image);\n    s->drawn = false;")
    source = source.replace("    TextureUpload u{it->second.tex, {}, w, th};",
                            """    if (std::getenv("NSMB2_TRACE_TEXTURE_UPLOADS") && changes >= 4 && changes % 120 == 0)
        LOG("dynamic texture %08x %ux%u format %u change %u", t.addr, t.width, t.height, t.format, changes);
    TextureUpload u{it->second.tex, {}, w, th};""")
    # Reuse decoded pixels for unchanged blocks of the animated ETC1A4 atlas.
    source = source.replace("    uint32_t changes = 0; // times",
                            "    std::vector<uint8_t> compressed, decoded;\n    uint32_t changes = 0; // times")
    source = source.replace("        u.rgba.resize(size_t(t.width) * t.height * 4);\n        decode_texture(t, u.rgba.data());",
                            """        if (t.format == 13 && t.bytes >= (256u << 10) && changes >= 2) {
            auto &cached = it->second;
            if (cached.decoded.empty()) {
                cached.decoded.resize(size_t(t.width) * t.height * 4);
                decode_texture(t, cached.decoded.data());
                cached.compressed.assign(t.data, t.data + t.bytes);
            } else {
                update_etc1a4(t, cached.compressed.data(), cached.decoded.data());
            }
            u.rgba = cached.decoded;
        } else {
            u.rgba.resize(size_t(t.width) * t.height * 4);
            decode_texture(t, u.rgba.data());
        }""")
    return source.replace("int32_t(hs), int32_t(vs), 0}}",
                          "int32_t(hs), int32_t(vs), top ? 16 * scale : 0}}")


def pica(source):
    source = source.replace('#include "gpu/gpu.h"', '#include "gpu/gpu.h"\n#include "pica_shader_jit.h"')
    source = source.replace("ShaderSetup vs;", "ShaderSetup vs;\nstatic uint64_t shader_revision = 0;")
    source = source.replace("            vs.code[at & 4095] = value;",
                            """            auto &word = vs.code[at & 4095];
            if (word != value) ++shader_revision;
            word = value;""")
    source = source.replace("            vs.swizzle[at & 127] = value;",
                            """            auto &word = vs.swizzle[at & 127];
            if (word != value) ++shader_revision;
            word = value;""")
    source = source.replace("Vertex shade(const Vec4 attrs[16], const OutputMap &map) {",
                            "Vertex shade(const Vec4 attrs[16], const OutputMap &map, CompiledVertex compiled = nullptr) {")
    source = source.replace("    run_shader(vs, regs[VS_ENTRY] & 0xFFFF, in, out);",
                            """    if (compiled) {
        Vec4 scratch[16]{};
        compiled(vs.f, in, out, scratch);
    } else {
        run_shader(vs, regs[VS_ENTRY] & 0xFFFF, in, out);
    }""")
    source = source.replace("    OutputMap map;\n", """    OutputMap map;
    static const bool interpret = std::getenv("NSMB2_INTERPRET_VERTEX") != nullptr;
    const auto compiled = interpret ? nullptr : find_compiled_shader(vs, regs[VS_ENTRY] & 0xFFFF, shader_revision);
""")
    source = source.replace("    int8_t semantic[16][4];\n    uint32_t mask;",
                            """    struct Component { uint8_t reg, channel, semantic; };
    Component components[28]{};
    uint32_t component_count = 0;
    uint8_t input_registers[16]{};
    uint32_t input_count = 0;""")
    source = source.replace("        std::memset(semantic, -1, sizeof semantic);\n        mask = regs[VS_OUTPUT_MASK] & 0xFFFF;",
                            """        const uint32_t mask = regs[VS_OUTPUT_MASK] & 0xFFFF;
        input_count = (regs[VS_INPUT_CONFIG] & 0xF) + 1;
        const uint64_t input_map = regs[VS_INPUT_MAP_LO] | (uint64_t(regs[VS_INPUT_MAP_HI]) << 32);
        for (uint32_t i = 0; i < input_count; ++i)
            input_registers[i] = uint8_t((input_map >> (4 * i)) & 0xF);""")
    source = source.replace("                semantic[reg][c] = sem < SEMANTIC_COUNT ? int8_t(sem) : -1;",
                            "                if (sem < SEMANTIC_COUNT)\n"
                            "                    components[component_count++] = {uint8_t(reg), uint8_t(c), uint8_t(sem)};")
    source = source.replace(
        between(source, "    uint32_t inputs = (regs[VS_INPUT_CONFIG]", "    if (compiled)"),
        "    for (uint32_t i = 0; i < map.input_count; ++i) in[map.input_registers[i]] = attrs[i];\n")
    source = source.replace(
        between(source, "    for (int r = 0; r < 16; r++)", "    // colors are clamped"),
        """    for (uint32_t i = 0; i < map.component_count; ++i) {
        const auto &component = map.components[i];
        v.a[component.semantic] = out[component.reg][component.channel];
    }
""")
    return source.replace("shade(attrs, map)", "shade(attrs, map, compiled)")


def shader(source):
    source = source.replace('#include "log.h"', '#include "log.h"\n#include "pica_shader_arithmetic.h"')
    source = source.replace(between(source, "// 0 * anything", "struct Frame"), "")
    source = source.replace(between(source, "    static const Vec4 ones", "    auto evaluate"), "")
    source = source.replace("    int32_t addr[3] = {0, 0, 0}; // a0.x, a0.y, aL",
                            "    int32_t addr[4] = {}; // constant zero, a0.x, a0.y, aL")
    source = source.replace("addr[2] += f.increment;", "addr[3] += f.increment;")
    source = source.replace("addr[2] = iu[1];", "addr[3] = iu[1];")
    return source.replace(between(source, "        // arithmetic:", "        // flow control"),
                          """        if (op < 0x20 || op >= 0x2E) {
            run_arithmetic(s, pc, ins, in, out, tmp, addr, cond);
            ++pc;
            continue;
        }

""")


def vertex_workers(source):
    source = source.replace("#include <condition_variable>", "#include <atomic>")
    source = source.replace(between(source, "        if (lanes == 1 || count < 64)", "    void slice("),
                            """        if (lanes == 1 || count < 256) return fn(0, count);
        job = &fn;
        job_count = count;
        pending.store(lanes - 1, std::memory_order_relaxed);
        generation.fetch_add(1, std::memory_order_release);
        generation.notify_all();
        slice(0, fn, count);
        for (int left = pending.load(std::memory_order_acquire); left;
             left = pending.load(std::memory_order_acquire))
            pending.wait(left, std::memory_order_acquire);
    }

private:
    int lanes = 1;
    std::atomic<int> pending{0};
    std::atomic<uint64_t> generation{0};
    size_t job_count = 0;
    const std::function<void(size_t, size_t)> *job = nullptr;

""")
    return source.replace(between(source, "        uint64_t seen = 0;", "\n};\n\nWorkers &workers"),
                          """        uint64_t seen = 0;
        for (;;) {
            generation.wait(seen, std::memory_order_acquire);
            seen = generation.load(std::memory_order_acquire);
            slice(lane, *job, job_count);
            if (pending.fetch_sub(1, std::memory_order_acq_rel) == 1) pending.notify_one();
        }
    }""")


def transfer(source):
    return source.replace("    auto src_offset = [&](uint32_t x, uint32_t y) {",
                          """    // These RGB565 transfers only untile/crop. Copy the packed pixels
    // directly, preserving all bits and visiting memory in tile order.
    if (in_fmt == FB_RGB565 && out_fmt == FB_RGB565 && !input_linear && !tiled_both &&
        !scale && w <= in_w && h <= in_h && (in_w % 8) == 0 && (w % 8) == 0 && (h % 8) == 0 &&
        (uintptr_t(src) + uint64_t(in_w) * in_h * 2 <= uintptr_t(dst) ||
         uintptr_t(dst) + uint64_t(w) * h * 2 <= uintptr_t(src))) {
        for (uint32_t y = 0; y < h; y += 8)
            for (uint32_t x = 0; x < w; x += 8) {
                const uint8_t *tile = src + 2 * (y * in_w + x * 8);
                for (uint32_t row = 0; row < 8; ++row) {
                    const uint32_t target_y = flip ? h - 1 - (y + row) : y + row;
                    uint8_t *target = dst + 2 * (target_y * w + x);
                    for (uint32_t col = 0; col < 8; col += 2)
                        std::memcpy(target + col * 2, tile + morton8(col, row) * 2, 4);
                }
            }
        return;
    }
    auto src_offset = [&](uint32_t x, uint32_t y) {""")


def texture(source):
    source = source.replace("void decode_texture(const Texture &t, uint8_t *rgba) {",
                          """void decode_texture(const Texture &t, uint8_t *rgba) {
    if (t.format == T_RGBA8) {
        for (uint32_t y = 0; y < t.height; y += 8)
            for (uint32_t x = 0; x < t.width; x += 8) {
                const uint8_t *tile = t.data + 4 * (y * t.width + x * 8);
                for (uint32_t row = 0; row < 8; ++row) {
                    auto *out = rgba + 4 * ((y + row) * t.width + x);
                    for (uint32_t col = 0; col < 8; ++col) {
                        uint32_t pixel;
                        std::memcpy(&pixel, tile + morton8(col, row) * 4, 4);
                        pixel = _byteswap_ulong(pixel);
                        std::memcpy(out + col * 4, &pixel, 4);
                    }
                }
            }
        return;
    }
    if (t.format == T_RGB565 || t.format == T_RGB5A1 || t.format == T_RGBA4) {
        const uint32_t format = t.format == T_RGB565 ? FB_RGB565 : t.format == T_RGB5A1 ? FB_RGB5A1 : FB_RGBA4;
        for (uint32_t y = 0; y < t.height; y += 8)
            for (uint32_t x = 0; x < t.width; x += 8) {
                const uint8_t *tile = t.data + 2 * (y * t.width + x * 8);
                for (uint32_t row = 0; row < 8; ++row) {
                    auto *out = rgba + 4 * ((y + row) * t.width + x);
                    for (uint32_t col = 0; col < 8; ++col) {
                        const Rgba pixel = fb_decode(format, tile + morton8(col, row) * 2);
                        std::memcpy(out + col * 4, &pixel, 4);
                    }
                }
            }
        return;
    }
    if (t.format == T_ETC1 || t.format == T_ETC1A4) {
        const bool alpha = t.format == T_ETC1A4;
        const uint32_t block_bytes = alpha ? 16 : 8;
        const auto *block = t.data;
        for (uint32_t y = 0; y < t.height; y += 8)
            for (uint32_t x = 0; x < t.width; x += 8)
                for (uint32_t dy = 0; dy < 8; dy += 4)
                    for (uint32_t dx = 0; dx < 8; dx += 4, block += block_bytes) {
                        uint64_t colors, alphas = UINT64_MAX;
                        if (alpha) std::memcpy(&alphas, block, 8);
                        std::memcpy(&colors, block + (alpha ? 8 : 0), 8);
                        for (uint32_t row = 0; row < 4; ++row) {
                            auto *out = rgba + 4 * ((y + dy + row) * t.width + x + dx);
                            for (uint32_t col = 0; col < 4; ++col) {
                                Rgba pixel = etc1(colors, col, row);
                                pixel.a = expand4(uint32_t(alphas >> (4 * (4 * col + row))) & 15);
                                std::memcpy(out + 4 * col, &pixel, 4);
                            }
                        }
                    }
        return;
    }""").replace("#include <algorithm>", "#include <algorithm>\n#include <cstring>")
    return source.replace("Rgba sample_texture(const Texture &t, float u, float v) {",
                          """void update_etc1a4(const Texture &t, uint8_t *previous, uint8_t *rgba) {
    const uint8_t *block = t.data;
    for (uint32_t y = 0; y < t.height; y += 8)
        for (uint32_t x = 0; x < t.width; x += 8)
            for (uint32_t dy = 0; dy < 8; dy += 4)
                for (uint32_t dx = 0; dx < 8; dx += 4, block += 16, previous += 16) {
                    if (!std::memcmp(previous, block, 16)) continue;
                    std::memcpy(previous, block, 16);
                    uint64_t colors, alphas;
                    std::memcpy(&alphas, block, 8);
                    std::memcpy(&colors, block + 8, 8);
                    for (uint32_t row = 0; row < 4; ++row) {
                        auto *out = rgba + 4 * ((y + dy + row) * t.width + x + dx);
                        for (uint32_t col = 0; col < 4; ++col) {
                            Rgba pixel = etc1(colors, col, row);
                            pixel.a = expand4(uint32_t(alphas >> (4 * (4 * col + row))) & 15);
                            std::memcpy(out + 4 * col, &pixel, 4);
                        }
                    }
                }
}

Rgba sample_texture(const Texture &t, float u, float v) {""")


def applets(source):
    return source.replace(
        '#include "log.h"', '#include "log.h"\n#include "memory.h"\n#include <cstring>\n#include <vector>').replace(
        "constexpr uint32_t SIGNAL_WAKEUP = 1;",
        "constexpr uint32_t SIGNAL_WAKEUP = 1;\n"
        "constexpr uint32_t APPID_ERROR = 0x406;\n"
        "constexpr uint32_t SIGNAL_RESPONSE = 3;\n"
        "constexpr uint32_t SIGNAL_WAKEUP_BY_EXIT = 10;\n"
        "constexpr uint32_t ERROR_PARAM_SIZE = 0xf80;\n"
        "constexpr uint32_t ERROR_RESULT_OFFSET = 0xf70;").replace(
        "namespace hle {\nnamespace {",
        "namespace hle {\nvoid reply_nsmb2_shared_font(Request &req);\nnamespace {").replace(
        "    Parameter parameter;",
        "    Parameter parameter;\n    bool error_applet_prepared = false;\n    std::vector<uint8_t> error_reply;").replace(
        "            r.push(0); // parameter data size",
        "            const auto size = parameter.signal == SIGNAL_WAKEUP_BY_EXIT\n"
        "                ? std::min<uint32_t>(req.arg(1), uint32_t(error_reply.size())) : 0;\n"
        "            r.push(size);").replace(
        "            r.push_handles({parameter.handle}, true);",
        """            auto handle = parameter.handle;
            if (handle && req.id() == 0x000E)
                handle = kernel::add_handle(kernel::get_handle(handle));
            r.push_handles({handle}, true);""").replace(
        "            req.push_static_buffer(r, 0, nullptr, 0);",
        "            req.push_static_buffer(r, 0, error_reply.data(), size);").replace(

        "app == APPID_APPLICATION || app == 0;",
        "app == APPID_APPLICATION || app == 0 || (app == APPID_ERROR && error_applet_prepared);").replace(
        "        case 0x004B:",
        """        case 0x000C: { // SendParameter: the error applet requests shared capture memory.
            if (!error_applet_prepared || req.arg(1) != APPID_ERROR ||
                req.arg(2) != 2 || req.arg(3) != 0x20) unimplemented(*this, req);
            const auto size = mem::read32(req.arg(7));
            if (!size || size > 0x00400000) {
                req.reply(1, 0, kernel::RESULT_INVALID_COMBINATION);
                break;
            }
            auto capture = std::make_shared<kernel::SharedMemory>();
            capture->name = "APT error capture";
            capture->size = size;
            req.reply(1, 0);
            send_parameter({APPID_ERROR, SIGNAL_RESPONSE, kernel::add_handle(capture)});
            break;
        }
        case 0x0018: // PrepareToStartLibraryApplet
            if (req.arg(0) != APPID_ERROR) unimplemented(*this, req);
            error_applet_prepared = true;
            req.reply(1, 0);
            break;
        case 0x001E: { // StartLibraryApplet
            if (!error_applet_prepared || req.arg(0) != APPID_ERROR || req.arg(1) != ERROR_PARAM_SIZE)
                unimplemented(*this, req);
            const auto *input = mem::ptr(req.arg(5));
            error_reply.assign(input, input + req.arg(1));
            // Report dismissal and no agreement. The game can continue in offline mode.
            std::fill_n(error_reply.begin() + ERROR_RESULT_OFFSET, 6, uint8_t{0});
            uint32_t code;
            std::memcpy(&code, input + 4, sizeof code);
            LOG("APT: dismissed error display (type %u, code %u)", input[0], code);
            error_applet_prepared = false;
            req.reply(1, 0);
            send_parameter({APPID_ERROR, SIGNAL_WAKEUP_BY_EXIT, 0});
            break;
        }
        case 0x0040: // SendCaptureBufferInfo
            if (!error_applet_prepared || req.arg(0) != 0x20) unimplemented(*this, req);
            req.reply(1, 0);
            break;
        case 0x0044: // GetSharedFont
            reply_nsmb2_shared_font(req);
            break;
        case 0x004B:""")


def prepare(upstream, output):
    for directory in ("src", "include"):
        shutil.copytree(upstream / directory, output / directory, dirs_exist_ok=True)
    src = output / "src"
    edit(src / "frontend/sdl.cpp", frontend)
    edit(src / "frontend/frontend.h", lambda source: source.replace(
        "const char *cli_dump, bool force_launcher, bool play", "const char *cli_dump"))
    edit(src / "frontend/games.h", lambda source: source.replace(
        'inline constexpr KnownDump KNOWN_DUMPS[] = {',
        'inline constexpr KnownDump KNOWN_DUMPS[] = {\n'
        '    {0x000400000007AF00, "nsmb2", "", "NewSuperMarioBros2", Region::EUR},'))
    edit(src / "platform.cpp", platform)
    edit(src / "frontend/settings.h", lambda source: source.replace(
        "    int volume = 100;", "    int volume = 25;"))
    edit(src / "frontend/settings.cpp", lambda source: source.replace(
        'else if (k == "volume") volume = std::atoi(v.c_str());',
        'else if (k == "volume") volume = std::clamp(std::atoi(v.c_str()), 0, 100);').replace(
        'else if (k == "language") language = std::clamp(std::atoi(v.c_str()), 1, 5);',
        'else if (k == "language") language = std::atoi(v.c_str());'))
    edit(src / "hle/cfg.cpp", lambda source: source.replace(
        '    default: return 110; // United Kingdom',
        '    case 8: return 94;  // Netherlands\n'
        '    case 9: return 98;  // Portugal\n'
        '    case 10: return 100; // Russia\n'
        '    default: return 110; // United Kingdom').replace(
        '            uint8_t language = l >= 1 && l <= 5 ? uint8_t(l) : LANGUAGE_ENGLISH;',
        '            const bool supported = (l >= 1 && l <= 5) || (l >= 8 && l <= 10);\n'
        '            uint8_t language = supported ? uint8_t(l) : LANGUAGE_ENGLISH;'))
    edit(src / "dump.h", lambda source: source.replace(
        "    uint64_t program_id() const",
        "    const auto &exefs_files() const { return exefs_files_; }\n    uint64_t program_id() const").replace(
        "    std::vector<uint8_t> exheader_, code_;",
        "    std::vector<uint8_t> exheader_, code_;\n    std::map<std::string, std::vector<uint8_t>> exefs_files_;"))
    edit(src / "dump.cpp", lambda source: source.replace(
        "    std::vector<uint8_t> exheader, code;",
        "    std::vector<uint8_t> exheader, code;\n    std::map<std::string, std::vector<uint8_t>> exefs_files;").replace(
        '        if (std::strncmp(reinterpret_cast<const char *>(e), ".code", 8) != 0) continue;',
        '''        const char *raw = reinterpret_cast<const char *>(e);
        std::string name(raw, strnlen(raw, 8));
        if (name == "icon" || name == "logo" || name == "banner") {
            uint64_t offset = uint64_t(u32(e + 8)) + 0x200;
            uint64_t size = u32(e + 12);
            if (offset + size > uint64_t(u32(h + 0x1A4)) * MEDIA_UNIT)
                fatal("Invalid ExeFS section: %s", name.c_str());
            auto &data = n.exefs_files[name];
            data.resize(size_t(size));
            read_at(exefs + offset, data.data(), data.size());
        }
        if (name != ".code") continue;''').replace(
        "    romfs_offset_ = game.romfs_offset",
        "    exefs_files_ = std::move(game.exefs_files);\n    romfs_offset_ = game.romfs_offset"))
    edit(src / "hle/gsp.cpp", lambda source: source.replace(
        "    void set_buffer(uint32_t screen, const uint32_t *info) {",
        "    void set_buffer(uint32_t screen, const uint32_t *info) {").replace(
        "        lcd[screen] = {info[1], info[3], info[4]};",
        "        if (screen == 0 && lcd[0].addr != info[1]) ++frames_rendered;\n"
        "        lcd[screen] = {info[1], info[3], info[4]};").replace(
        "            if ((c[3] >> 16) == 400) frames_rendered++;\n", "").replace(
        "    uint32_t frames_rendered = 0; // display transfers to the top screen, for YW2_FPS",
        "    uint32_t frames_rendered = 0; // new top-screen buffers for NSMB2_FPS\n"
        "    std::chrono::steady_clock::time_point fps_since = std::chrono::steady_clock::now();").replace(
        "            pica::SceneInfo si = pica::scene_info();",
        "            const auto now = std::chrono::steady_clock::now();\n"
        "            const double seconds = std::chrono::duration<double>(now - fps_since).count();\n"
        "            fps_since = now;\n"
        "            pica::SceneInfo si = pica::scene_info();").replace(
        "frames_rendered / 5.0", "frames_rendered / seconds"))
    edit(src / "video/gpu/gpu.cpp", gpu)
    edit(src / "video/pica.cpp", lambda source: vertex_workers(pica(source)))
    edit(src / "video/shader.cpp", shader)
    edit(src / "video/transfer.cpp", transfer)
    edit(src / "video/internal.h", lambda source: source.replace(
        "void decode_texture(const Texture &t, uint8_t *rgba);",
        "void decode_texture(const Texture &t, uint8_t *rgba);\n"
        "void update_etc1a4(const Texture &t, uint8_t *previous, uint8_t *rgba);"))
    edit(src / "video/texture.cpp", texture)
    edit(src / "hle/fs.cpp", filesystem)
    edit(src / "hle/apt.cpp", applets)
    # The SDK puts the result immediately after the error type/revision word.
    edit(src / "hle/err.cpp", lambda source: source.replace(
        "name, w[2], w[3], w[6], w[5]", "name, w[1], w[2], w[6], w[5]"))
    for path in src.rglob("*"):
        if path.suffix in (".h", ".cpp"):
            content = path.read_text(encoding="utf-8")
            if "YW2_" in content:
                path.write_text(content.replace("YW2_", "NSMB2_"), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.upstream, args.output)






















