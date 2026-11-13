# New Super Mario Bros. 2 Recompiled

Experimental native Windows x64 port of the European Nintendo 3DS release (`CTR-P-ABEP`). The build translates the original ARM and Thumb code to C and compiles it for x64. It reads the original game resources from a local cartridge image.

## Quick start

1. Install Python 3.11 or newer and the Visual Studio **Desktop development with C++** workload. See [BUILD.md](BUILD.md) for the required components.
2. Extract the source ZIP and open the folder that contains `build.cmd` in File Explorer. Put your decrypted European `.3ds` ROM in that folder.
3. Type `cmd` in the File Explorer address bar and press Enter. Run this command, replacing `Yourrom.3ds` with the name of your ROM file.

   ```bat
   build.cmd -Cartridge "Yourrom.3ds" -Language en
   ```

4. When the build finishes, open `dist/NewSuperMarioBros2.exe`.

Use `-Language fr` to play in French. See [BUILD.md](BUILD.md) for all eight languages and the manual build steps. [PROGRESS.md](PROGRESS.md) lists the features tested so far.

## Default controls

| 3DS input | Keyboard and mouse | Xbox controller | PlayStation controller |
| --- | --- | --- | --- |
| Circle Pad | W, A, S, D (Z, Q, S, D on AZERTY) | Left stick | Left stick |
| D-Pad | Arrow keys | D-Pad | D-Pad |
| A | K | B | Circle |
| B | J | A | Cross |
| X | I | Y | Triangle |
| Y | U | X | Square |
| L | Q (A on AZERTY) | LB | L1 |
| R | E | RB | R1 |
| ZL | 1 (number row) | LT | L2 |
| ZR | 3 (number row) | RT | R2 |
| Start | Enter | Menu | Options |
| Select | Backspace | View | Share / Create |
| Touch screen | Left-click or drag on the lower screen | | |

### PC shortcuts

| Shortcut | Action |
| --- | --- |
| Tab or right stick click (R3) | Swap the two screens |
| F5 | Cycle adaptive layouts for the current scene when single-screen mode and adaptive layout are active and the screens are in their default order |
| F6 | Toggle adaptive layout |
| F7 | Toggle widescreen |
| F8 | Toggle picture-in-picture |
| F9 | Toggle single-screen mode |
| F10 | Start or stop dumping textures for debugging |
| F11 | Toggle fullscreen |
| F12 | Take a screenshot and save diagnostic logs |
| Shift+F12 | Capture a burst of screenshots and rendering diagnostics |
