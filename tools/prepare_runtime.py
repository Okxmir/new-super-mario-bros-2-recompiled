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
    source = source.replace('    if (!window) fatal("cannot create window: %s", SDL_GetError());',
                            '    if (!window) fatal("cannot create window: %s", SDL_GetError());\n'
                            '    SDL_RaiseWindow(window);')
    source = source.replace(
        "    SDL_SetWindowFullscreen(window, s.fullscreen); // the game's own choice, whatever the launcher was",
        "    if (s.fullscreen) SDL_SetWindowFullscreen(window, true);\n"
        "    SDL_RaiseWindow(window);")
    source = source.replace("    fatal_hook = show_fatal;",
                            '    if (!std::getenv("NSMB2_NO_DIALOG")) fatal_hook = show_fatal;')
    source = source.replace(
        "            SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_SPIRV_BOOLEAN, true);",
        "            SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_SHADERS_SPIRV_BOOLEAN, true);\n"
        "            SDL_SetBooleanProperty(props, SDL_PROP_GPU_DEVICE_CREATE_DEBUGMODE_BOOLEAN, false);")
    source = source.replace(
        "    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMEPAD | SDL_INIT_AUDIO)) {",
        """    // SDL's HIDAPI scan can block on the standard USB DualSense.
    // Leave that device to Windows and keep HIDAPI available for other controllers.
    SDL_SetHintWithPriority(SDL_HINT_HIDAPI_IGNORE_DEVICES, "0x054c/0x0ce6", SDL_HINT_DEFAULT);
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO)) {""",
    )
    source = source.replace(
        "    if (SDL_JoystickID *ids = SDL_GetGamepads(&count)) {",
        """    if (!SDL_InitSubSystem(SDL_INIT_GAMEPAD))
        LOG("gamepad initialization failed: %s", SDL_GetError());
    if (SDL_JoystickID *ids = SDL_GetGamepads(&count)) {""",
    )
    source = source.replace(
        "    std::vector<SDL_Gamepad *> pads;",
        """    std::vector<SDL_Gamepad *> pads;
    auto open_gamepad = [&](SDL_JoystickID id) {
        if (SDL_Gamepad *pad = SDL_OpenGamepad(id)) {
            pads.push_back(pad);
            const char *name = SDL_GetGamepadName(pad);
            LOG("gamepad connected: %s", name ? name : "Unknown controller");
        }
    };""",
    )
    source = source.replace(
        "            if (SDL_Gamepad *g = SDL_OpenGamepad(ids[j])) pads.push_back(g);",
        "            open_gamepad(ids[j]);",
    ).replace(
        "                    if (SDL_Gamepad *g = SDL_OpenGamepad(e.gdevice.which)) pads.push_back(g);",
        "                    open_gamepad(e.gdevice.which);",
    )
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
    source = source.replace(
        "uint32_t cfmt = (regs[COLOR_FORMAT] >> 16) & 7, dfmt = regs[DEPTH_FORMAT] & 3;",
        "const uint32_t cfmt = render_target_format(regs[COLOR_FORMAT]);\n"
        "    const uint32_t dfmt = regs[DEPTH_FORMAT] & 3;")
    source = source.replace("    if (in_h == 400) { // a top-screen frame is done",
                            """    // Mario's RGB565 buffers have 256 rows per column. The top
    // LCD starts 16 columns into a 416-column framebuffer.
    const bool top = in_w == 256 && in_h == 416 && out_w == 256 && out_h == 416 && flags == 0x2200;
    const bool bottom = in_w == 256 && in_h == 416 && out_w == 256 && out_h == 320 && flags == 0x2204;
    if (top) { // a top-screen transfer""")
    source = source.replace("    bool top = in_h == 400;\n", "")
    source = source.replace("    bool to_lcd = !(flags & 2) && !(flags & 0x20) && (((flags >> 12) & 7) <= 1);",
                            "    const bool to_lcd = top || bottom;")
    source = source.replace(
        "if (!s->depth && s->addr == p && s->width == in_w && s->height == in_h) src = s.get();",
        "if (!s->depth && s->addr == p && s->width == in_w && s->height == in_h &&\n"
        "            s->format == ((flags >> 8) & 7)) src = s.get();")
    source = source.replace(
        "    const bool to_lcd = top || bottom;",
        """    const bool to_lcd = top || bottom;
    uint32_t source_row = top ? 16 : 0;
    bool aliased = false;
    if (!src && bottom) {
        // The lower LCD can read a tile-row-aligned view into the main render target.
        // Keep that crop on the GPU instead of downloading the entire target each frame.
        for (auto &s : surfaces) {
            if (s->depth || s->reload || s->format != FB_RGB565 || s->width != in_w ||
                p <= s->addr || p >= uint64_t(s->addr) + s->bytes()) continue;
            const uint32_t offset = p - s->addr;
            const uint32_t pitch = s->width * s->bpp();
            const uint32_t row = offset / pitch;
            if (offset % (8 * pitch) || row + out_h > s->height) continue;
            if (!src || s->last_used >= src->last_used) {
                src = s.get();
                source_row = row;
                aliased = true;
            }
        }
    }""")
    source = source.replace(
        "    flush();\n    uint32_t hs =",
        "    flush();\n    if (aliased && overwritten(src)) return false;\n    uint32_t hs =")
    source = source.replace("    int w = int(src->th >> vs), h = int(src->tw >> hs); // upright: rows of the output become columns\n    (void)out_w, (void)out_h;",
                            """    const int scale = src->scale;
    const int w = (top ? 400 : 320) * scale, h = 240 * scale;
    const uint32_t lcd_address = out + (top ? 16 * 256 * 2 : 0);""")
    source = source.replace("    LcdFrames &f = lcd[out];", "    LcdFrames &f = lcd[lcd_address];")
    source = source.replace("struct LcdFrames {", "struct LcdFrames {\n    uint32_t scanout_bytes = 0;")
    source = source.replace("    LcdFrames &f = lcd[lcd_address];",
                            "    LcdFrames &f = lcd[lcd_address];\n"
                            "    f.scanout_bytes = uint32_t(top ? 400 : 320) * 256 * 2;")
    source = source.replace("    lcd.erase(addr); // an LCD buffer written by the CPU shows that, not an older GPU frame",
                            """    for (auto &[address, frame] : lcd) {
        const uint32_t lcd_start = to_physical(address);
        if (p < uint64_t(lcd_start) + frame.scanout_bytes && lcd_start < uint64_t(p) + size) {
            frame.latest = -1;
            if (address == top_queue.addr) top_queue.reset();
        }
    }""")
    source = source.replace("    if (addr == top_queue.addr) top_queue.reset();\n", "")
    source = source.replace(
        """        SDL_GPUTexture *staging = make_texture(l.surface->width, l.surface->height, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
                                               SDL_GPU_TEXTUREUSAGE_SAMPLER);
        loaded.push_back(staging);
        items.push_back({at, staging, l.surface->width, l.surface->height});""",
        """        auto &surface = *l.surface;
        const bool direct = surface.tw == surface.width && surface.th == surface.height;
        SDL_GPUTexture *staging = direct ? nullptr :
            make_texture(surface.width, surface.height, SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM,
                         SDL_GPU_TEXTUREUSAGE_SAMPLER);
        loaded.push_back(staging);
        if (direct || staging)
            items.push_back({at, direct ? surface.tex : staging, surface.width, surface.height});
        else
            surface.reload = true;""")
    source = source.replace(
        "        Surface *s = surface_loads[i].surface;",
        "        if (!loaded[i]) continue;\n        Surface *s = surface_loads[i].surface;")
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
    source = source.replace(
        "    tri_ids.push_back(tri);",
        "    if (interp_on) tri_ids.push_back(tri);",
    )
    source = source.replace("#include <cmath>", "#include <cmath>\n#include <immintrin.h>")
    source = source.replace(
        """            float x0 = v0.a[POS] / w0, y0 = v0.a[POS + 1] / w0, x1 = v1.a[POS] / w1, y1 = v1.a[POS + 1] / w1;
            float x2 = v2.a[POS] / w2, y2 = v2.a[POS + 1] / w2;""",
        """            alignas(16) float xy[4], last[4];
            _mm_store_ps(xy, _mm_div_ps(_mm_setr_ps(v0.a[POS], v0.a[POS + 1], v1.a[POS], v1.a[POS + 1]),
                                      _mm_setr_ps(w0, w0, w1, w1)));
            _mm_store_ps(last, _mm_div_ps(_mm_setr_ps(v2.a[POS], v2.a[POS + 1], 0.0f, 0.0f), _mm_set1_ps(w2)));
            const float x0 = xy[0], y0 = xy[1], x1 = xy[2], y1 = xy[3], x2 = last[0], y2 = last[1];""",
    )
    source = source.replace(
        """        for (int c = 0; c < 4; c++) g.color[c] = a[COLOR + c], g.quat[c] = a[QUAT + c];
        g.tc01[0] = a[TEX0], g.tc01[1] = a[TEX0 + 1], g.tc01[2] = a[TEX1], g.tc01[3] = a[TEX1 + 1];""",
        """        _mm_storeu_ps(g.color, _mm_loadu_ps(a + COLOR));
        _mm_storeu_ps(g.quat, _mm_loadu_ps(a + QUAT));
        _mm_storeu_ps(g.tc01, _mm_loadu_ps(a + TEX0));""",
    )
    source = source.replace(
        "    for (auto &l : surface_loads) reloaded.push_back(l.surface);",
        "    if (interp_this) for (auto &l : surface_loads) reloaded.push_back(l.surface);",
    )
    source = reuse_upload_buffer(source)
    return source.replace("int32_t(hs), int32_t(vs), 0}}",
                          "int32_t(hs), int32_t(vs), (int(source_row) + src->margin) * scale}}").replace(
        "q.last_push = vblanks.load(), q.addr = out;",
        "q.last_push = vblanks.load(), q.addr = lcd_address;")


def reuse_upload_buffer(source):
    source = source.replace(
        "// copies pending texture, LUT, surface and vertex data to the GPU (one copy pass)",
        """// Keep the transfer buffer across batches. SDL cycles its backing storage\n// when commands from an earlier batch still reference it.
SDL_GPUTransferBuffer *batch_upload = nullptr;
uint32_t upload_capacity = 0;

uint32_t batch_capacity(size_t size) {
    return uint32_t(std::min<uint64_t>(UINT32_MAX, std::max<uint64_t>(65536, uint64_t(size) * 2)));
}

// copies pending texture, LUT, surface and vertex data to the GPU (one copy pass)""")
    source = source.replace(
        """    SDL_GPUTransferBufferCreateInfo tbi{SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD, uint32_t(total), 0};
    SDL_GPUTransferBuffer *tb = SDL_CreateGPUTransferBuffer(dev, &tbi);
    if (!tb) out_of_gpu_memory(), tb = SDL_CreateGPUTransferBuffer(dev, &tbi);
    if (!tb) {""",
        """    if (total > upload_capacity && total <= UINT32_MAX) {
        SDL_GPUTransferBufferCreateInfo info{SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD, batch_capacity(total), 0};
        if (auto *larger = SDL_CreateGPUTransferBuffer(dev, &info)) {
            if (batch_upload) SDL_ReleaseGPUTransferBuffer(dev, batch_upload);
            batch_upload = larger;
            upload_capacity = info.size;
        }
    }
    SDL_GPUTransferBuffer *tb = total <= upload_capacity ? batch_upload : nullptr;
    auto *map = tb ? static_cast<uint8_t *>(SDL_MapGPUTransferBuffer(dev, tb, true)) : nullptr;
    if (!map) {""")
    source = source.replace(
        "    auto *map = static_cast<uint8_t *>(SDL_MapGPUTransferBuffer(dev, tb, false));\n    size_t at = 0;",
        "    size_t at = 0;")
    source = source.replace("    SDL_EndGPUCopyPass(copy);\n    SDL_ReleaseGPUTransferBuffer(dev, tb);\n\n    // surface loads",
                            "    SDL_EndGPUCopyPass(copy);\n\n    // surface loads")
    return source


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
        // Generated code supplies zero for unwritten temporaries.
        Vec4 scratch[16];
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
    source = source.replace(
        "            for (uint32_t c = 0; c < a.count; c++) {",
        """            if (a.type == 3) {
                // Float vertex arrays dominate Mario's meshes. Load exactly
                // the declared components, including tightly packed XYZ.
                switch (a.count) {
                    case 4: std::memcpy(v.v, p, 16); break;
                    case 3: std::memcpy(v.v, p, 12); break;
                    case 2: std::memcpy(v.v, p, 8); break;
                    default: std::memcpy(v.v, p, 4); break;
                }
                out[i] = v;
                continue;
            }
            for (uint32_t c = 0; c < a.count; c++) {""",
    ).replace("                default: std::memcpy(&v[c], p + 4 * c, 4);", "")
    source = source.replace(
        "        for (auto &e : cache) e.index = ~0u;",
        "        if (indexed) for (auto &e : cache) e.index = ~0u;",
    )
    source = source.replace("#include <cmath>", "#include <cmath>\n#include <immintrin.h>")
    source = source.replace(
        "    for (int c = 0; c < 4; c++) v.a[COLOR + c] = std::fmin(std::fabs(v.a[COLOR + c]), 1.0f);",
        """    const __m128 color = _mm_loadu_ps(v.a + COLOR);
    const __m128 magnitude = _mm_andnot_ps(_mm_set1_ps(-0.0f), color);
    // MINPS selects the second operand for NaN, matching fmin here.
    _mm_storeu_ps(v.a + COLOR, _mm_min_ps(magnitude, _mm_set1_ps(1.0f)));""",
    )
    source = source.replace(
        "    if (n >= 512) {",
        """    if (n >= 512 && !indexed) {
        // Sequential draws have no repeated indices to look up or restore.
        static std::vector<Vertex> shaded;
        shaded.resize(n);
        const uint32_t first = regs[VERTEX_OFFSET];
        workers().run(n, [&](size_t begin, size_t end) {
            Vec4 attrs[16];
            for (size_t k = begin; k < end; ++k) {
                loader.read(first + uint32_t(k), attrs);
                shaded[k] = shade(attrs, map);
            }
        });
        for (const Vertex &v : shaded) assembler.push(v);
        w = shaded.back().a[POS + 3];
    } else if (n >= 512) {""",
    )
    source = source.replace(
        "    void push(const Vertex &v) {",
        """    template <class VertexAt>
    void push_range(uint32_t count, VertexAt vertex_at) {
        const uint32_t topology = (regs[PRIMITIVE_CONFIG] >> 8) & 3;
        uint32_t i = 0;
        if (topology != 1 && topology != 2 && list_count == 0) {
            // Complete lists can be emitted directly from the shaded vertices.
            for (; count - i >= 3; i += 3)
                emit_triangle(vertex_at(i), vertex_at(i + 1), vertex_at(i + 2));
        }
        for (; i < count; ++i) push(vertex_at(i));
    }

    void push(const Vertex &v) {""",
    ).replace(
        "        for (const Vertex &v : shaded) assembler.push(v);",
        "        assembler.push_range(n, [&](uint32_t i) -> const Vertex & { return shaded[i]; });",
    ).replace(
        "        for (uint32_t i = 0; i < n; i++) assembler.push(shaded[size_t(slot[index_at(i)])]);",
        """        assembler.push_range(n, [&](uint32_t i) -> const Vertex & {
            return shaded[size_t(slot[index_at(i)])];
        });""",
    )
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
    source = source.replace("#include <thread>", "#include <thread>\n#include <bit>\n#include <windows.h>")
    source = source.replace(
        "        unsigned hw = std::thread::hardware_concurrency();",
        """        unsigned hw = std::thread::hardware_concurrency();
        DWORD_PTR allowed = 0, system = 0;
        if (GetProcessAffinityMask(GetCurrentProcess(), &allowed, &system) && allowed)
            hw = std::popcount(allowed);""",
    )
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
    edit(src / "video/color.h", lambda source: source.replace(
        "inline uint32_t fb_bpp(uint32_t format)",
        """// The PICA render-target register swaps the two 16-bit format IDs used by GX and LCD.
inline uint32_t render_target_format(uint32_t reg) {
    uint32_t format = (reg >> 16) & 7;
    if (format == 2) return FB_RGB5A1;
    if (format == 3) return FB_RGB565;
    return format;
}

inline uint32_t fb_bpp(uint32_t format)"""))
    edit(src / "video/gpu/gpu.cpp", gpu)
    edit(src / "video/pica.cpp", lambda source: vertex_workers(pica(source)))
    edit(src / "video/raster.cpp", lambda source: source.replace(
        "cur.color_format = (regs[COLOR_FORMAT] >> 16) & 7;",
        "cur.color_format = render_target_format(regs[COLOR_FORMAT]);"))
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






















