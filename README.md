# New Super Mario Bros. 2 Recompiled

Experimental native Windows x64 port of the European Nintendo 3DS release (`CTR-P-ABEP`). The build translates the original ARM and Thumb code to C and compiles it for x64. It reads the original game resources from a local cartridge image.

Install Python 3.11 or newer and the **Desktop development with C++** workload for Visual Studio, including CMake tools and the Windows SDK. Put your European cartridge image in this folder and run the following in Command Prompt.

```bat
build.cmd -Cartridge "C:\FolderWhereIsTheRom\Rom.3ds" -Language en
```

Open `dist/NewSuperMarioBros2.exe` after the build passes. See [BUILD.md](BUILD.md) for the eight language options and manual build steps. [PROGRESS.md](PROGRESS.md) lists the features tested so far.
