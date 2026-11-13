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
