# Progress

| Component | Status |
| --- | --- |
| Cartridge and code | Verified the local European dump, extracted ExeFS and RomFS, and linked ARM/Thumb translations into a Windows x64 executable. |
| Boot and solo play | Verified first-run screens, title, file selection, opening cutscene, World 1 map, and entering World 1-1. |
| World 1-1 | Observed movement, jumps, an enemy interaction, collecting coins, returning to the map after losing a life, and re-entering the level. |
| Rendering | Vulkan and the software renderer use the PICA render-target format for LCD colors. Verified the HUD and course-to-map transition in the World 1 tower on both renderers. |
| Audio | The DSP initialized and the local stereo capture contained nonzero audio samples. |
| Save files | The game created its original `BigRedSave.dat`. Local archive format metadata and reformat backups are implemented. Completion and reload of a cleared course still need validation. |
| Build | `build.cmd` passed from a source-only copy with pinned dependency archives cached. It extracted the specified cartridge, generated code, built the program, ran the automated tests and produced the local distribution folder. |

The rest of the campaign, renderer parity with original hardware, gamepad behavior, DLC, and multiplayer still need validation. The first-run SpotPass flow supports dismissing the offline error and continuing into local play.

## Performance

On the RTX 3080 Ti test PC with Vulkan, after caching the unchanged blocks of the animated 1024 × 1024 ETC1A4 atlas, measured World 1-1 gameplay settled at 59.4–59.8 FPS over repeated five-second samples. The opening and World 1 map transition reached roughly 37–49 FPS in the slowest sampled sections. These measurements cover the tested route and hardware.

The automated tests cover cartridge integrity, execution of the original BSS routine, ETC1A4 block updates, and RGB565 color preservation through display transfers.

## Local diagnostics

Run `python tools/boot_probe.py --graphics` from the project directory to start an isolated boot test. Set `NSMB2_FPS=1` for the game to log distinct top-screen buffer flips per second. Captures and measurements in `logs/` are local.


