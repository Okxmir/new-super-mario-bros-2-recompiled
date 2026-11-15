#pragma once

#include <SDL3/SDL.h>
#include <windows.h>
#include <commctrl.h>

// The Windows SDK defines this name as a macro. The SDL layout uses it as a local variable.
#undef small

#include "frontend/settings.h"
#include "log.h"
#include "video/pica.h"

#pragma comment(lib, "comctl32.lib")

namespace frontend {

class ResolutionMenu {
public:
    ResolutionMenu(SDL_Window *window, Settings &settings) : settings_(settings) {
        hwnd_ = static_cast<HWND>(SDL_GetPointerProperty(
            SDL_GetWindowProperties(window), SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
        if (!hwnd_) return;

        bar_ = CreateMenu();
        choices_ = CreatePopupMenu();
        if (!bar_ || !choices_ || !AppendMenuW(bar_, MF_POPUP, reinterpret_cast<UINT_PTR>(choices_), label(settings.language))) {
            if (choices_) DestroyMenu(choices_);
            if (bar_) DestroyMenu(bar_);
            bar_ = choices_ = nullptr;
            LOG("window: could not create the resolution menu");
            return;
        }

        if (!AppendMenuW(choices_, MF_STRING, first_command, L"1\u00d7") ||
            !AppendMenuW(choices_, MF_STRING, first_command + 1, L"2\u00d7") ||
            !AppendMenuW(choices_, MF_STRING, first_command + 2, L"4\u00d7") ||
            !SetWindowSubclass(hwnd_, window_proc, subclass_id, reinterpret_cast<DWORD_PTR>(this))) {
            DestroyMenu(bar_);
            bar_ = choices_ = nullptr;
            LOG("window: could not install the resolution menu");
            return;
        }
        update_checks();
    }

    ~ResolutionMenu() {
        if (!bar_) return;
        if (IsWindow(hwnd_)) {
            RemoveWindowSubclass(hwnd_, window_proc, subclass_id);
            set_visible(false);
        }
        DestroyMenu(bar_);
    }

    ResolutionMenu(const ResolutionMenu &) = delete;
    ResolutionMenu &operator=(const ResolutionMenu &) = delete;

    void set_visible(bool visible) const {
        if (!bar_) return;
        const HMENU menu = visible ? bar_ : nullptr;
        if (GetMenu(hwnd_) != menu && SetMenu(hwnd_, menu)) DrawMenuBar(hwnd_);
    }

private:
    static constexpr UINT_PTR subclass_id = 1;
    static constexpr UINT first_command = 0x5100;
    static constexpr int scales[] = {1, 2, 4};

    static const wchar_t *label(int language) {
        switch (language) {
        case 2: return L"&Résolution";
        case 3: return L"&Auflösung";
        case 4: return L"&Risoluzione";
        case 5: return L"&Resolución";
        case 8: return L"&Resolutie";
        case 9: return L"&Resolução";
        case 10: return L"&Разрешение";
        default: return L"&Resolution";
        }
    }

    void update_checks() const {
        for (UINT i = 0; i < 3; ++i) {
            CheckMenuItem(choices_, first_command + i,
                          MF_BYCOMMAND | (scales[i] == settings_.resolution ? MF_CHECKED : MF_UNCHECKED));
        }
    }

    static LRESULT CALLBACK window_proc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam,
                                        UINT_PTR, DWORD_PTR data) {
        auto &menu = *reinterpret_cast<ResolutionMenu *>(data);
        if (message == WM_COMMAND && HIWORD(wparam) == 0 && lparam == 0) {
            const UINT command = LOWORD(wparam);
            if (command >= first_command && command < first_command + 3) {
                const int scale = scales[command - first_command];
                if (menu.settings_.resolution != scale) {
                    menu.settings_.resolution = scale;
                    pica::set_resolution_scale(scale);
                    menu.settings_.save();
                    menu.update_checks();
                    LOG("graphics: resolution set to %dx", scale);
                }
                return 0;
            }
        }
        return DefSubclassProc(hwnd, message, wparam, lparam);
    }

    Settings &settings_;
    HWND hwnd_ = nullptr;
    HMENU bar_ = nullptr;
    HMENU choices_ = nullptr;
};

} // namespace frontend
