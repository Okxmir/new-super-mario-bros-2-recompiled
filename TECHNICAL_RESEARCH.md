# Technical research

## Cartridge

| Field | Verified value |
| --- | --- |
| Format | 512 MiB NCSD, decrypted NCCH application |
| SHA-256 | `DE52D6F5775B6452584C17405CD583FDD50760A762CAD80091510C59B562033C` |
| Title and region | `CTR-P-ABEP`, `000400000007AF00`, `BIGRED`, SMDH mask `0xC` |
| Revision | ExHeader remaster field 0, NCCH format 2 |
| Code | Reverse LZSS, 0x503000 bytes decompressed |
| Code SHA-256 | `596068EDC3508AA8822CC389461B585D530875B02A66070FC0AF25FE88E98C94` |
| Memory map | Text `00100000+469484`, rodata `0056A000+6F5CC`, data `005DA000+28F40`, BSS `00602F40+BEEB4` |
| Resources | 1,232 RomFS entries, no CRO/CRS/CRR modules detected |
| Integrity | Three NCCH region hashes, four ExeFS entries, 86,117 RomFS IVFC block hashes |

The RomFS contains separate layouts, messages, courses, models, shaders, and audio. It includes European Dutch, English, French, German, Italian, Portuguese, Russian and Spanish directories. File presence and in-game language support are separate checks. [NCSD format](https://www.3dbrew.org/wiki/NCSD) · [ExHeader format](https://www.3dbrew.org/wiki/Exheader)

## Recompilation

The build uses the MIT-licensed Clockwork C emitter at revision `3047d9e990be4ac2c84174cb570dfec569c882e9`. It found 31,370 function entries. The native runtime supplies the ARM register state, 32-bit guest addresses, system services and PICA200 rendering. MSVC links the generated code into one title-specific program. [Clockwork](https://github.com/watchmakerers/clockwork/tree/3047d9e990be4ac2c84174cb570dfec569c882e9)

Capstone confirmed that the entry at `00100000` calls a BSS clearing loop at `00100024`. The loop reads the boundaries from literals at `00100040` and `00100044`. The native test fills the BSS and its boundary bytes with sentinels before calling the translated function. Ghidra p-code and LLVM IR are useful for investigating unresolved routines. A new lifter would require validating ARM/Thumb mode switches, flags, VFP and indirect calls already covered by the emitter. [Capstone](https://www.capstone-engine.org/arch.html) · [Ghidra p-code](https://ghidra.re/ghidra_docs/languages/html/pcoderef.html) · [LLVM IR](https://llvm.org/docs/LangRef.html)

The original startup requests the Mii archive `0004009B00010202`, the APT shared font and SelfNCCH ExeFS data. The Windows runtime opens a generated Mii RomFS, maps a relocated BCFNT font, and reads icon, banner and logo bytes from the local cartridge. [System archives](https://www.3dbrew.org/wiki/Title_list#0004009B_-_Shared_Data_Archives) · [3DS system font](https://www.3dbrew.org/wiki/System_Font)

## Graphics

The title uses rotated RGB565 buffers. The top LCD starts at column 16 of a 416-column buffer with a stride of 256 pixels. The Vulkan pass crops that padding, preserves RGB565 quantization and avoids reading the display image back to the CPU. A separate measured FPS counter counts top-screen buffer flips over elapsed wall time. Neither frame interpolation nor a change to game timing is required for these measurements.

The World 1-1 draw stream updates a 1024 × 1024 ETC1A4 atlas repeatedly. The renderer compares each compressed 4 × 4 block and reuses the decoded pixels for blocks whose complete 16-byte representation matches. It still uploads the complete texture to preserve draw ordering. Full decompression and the incremental update use the same ETC1 color decoder and alpha expansion.
