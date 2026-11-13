# Build and run on Windows

## What you need

- Windows 10 or 11, 64-bit.
- [64-bit Python 3.11 or newer](https://www.python.org/downloads/windows/) with pip. Enable **Add Python to PATH** in the installer. Open a new terminal and check that `python --version` and `python -m pip --version` both work.
- [Visual Studio](https://visualstudio.microsoft.com/downloads/) with the **Desktop development with C++** workload. In Visual Studio Installer, include the MSVC x64 build tools, a Windows SDK, and **C++ CMake tools for Windows**.
- A decrypted image of your own European **New Super Mario Bros. 2** cartridge, product code `CTR-P-ABEP` (original revision). The examples use a `.3ds` file. Use the actual path to your copy, including its filename.
- Internet access for the first build so the preparation script can fetch the build dependencies.

Extract the source files to a writable folder. Open the source folder that contains `build.cmd`, `CMakeLists.txt`, and `scripts` in File Explorer. To open Command Prompt there, type `cmd` in the address bar and press Enter. Close any running copy of the game before rebuilding.

## Build with one command

In **Command Prompt (cmd)**, run the following command with the path to your cartridge image.

```bat
build.cmd -Cartridge "C:\Games\New Super Mario Bros. 2 (Europe).3ds" -Language en
```

In **PowerShell**, use this form.

```powershell
.\build.cmd -Cartridge "C:\Games\New Super Mario Bros. 2 (Europe).3ds" -Language en
```

If you have exactly one cartridge image (`.3ds`, `.cci`, or `.cxi`) in the source folder, you can omit `-Cartridge` and its path.

The command prepares the cartridge and dependencies, compiles the optimized Windows x64 build, runs the tests and copies the playable files into `dist`. The first build can take several minutes.

### Choose the game language

Use any of the eight languages from the European cartridge.

| Option | Game language | `language` in `settings.ini` |
| --- | --- | --- |
| `en` | English | 1 |
| `fr` | French | 2 |
| `de` | German | 3 |
| `it` | Italian | 4 |
| `es` | Spanish | 5 |
| `nl` | Dutch | 8 |
| `pt` | Portuguese | 9 |
| `ru` | Russian | 10 |

`-Language` sets the language for the game in `dist`. If you omit it, the game keeps its current language and a fresh installation uses English. To switch languages after building, close the game and add or update the `language` line in `dist/userdata/settings.ini`. For example, use `language=2` for French.

## Build manually in PowerShell

Run the commands below one step at a time from the source folder. If a step reports an error, resolve it before continuing.

1. Open a Windows PowerShell session that can run the project's scripts. This execution policy applies only to the session it opens.

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass
   ```

2. Prepare the cartridge. This checks the image, extracts the local game data, translates the original ARM and Thumb code, and prepares the dependencies.

   ```powershell
   .\scripts\prepare.ps1 -Cartridge "C:\Games\New Super Mario Bros. 2 (Europe).3ds"
   ```

3. Compile the optimized Release build. Keep the leading dot and space on the first line so the second line can call the build function.

   ```powershell
   . .\scripts\common.ps1
   Build-Nsmb2 Release OFF
   ```

4. Run the tests. The current suite should report three passed tests.

   ```powershell
   .\scripts\run_tests.ps1 -Configuration Release
   ```

5. Prepare the playable folder. The command copies the executable, SDL, and the prepared local game files into `dist`.

   ```powershell
   .\scripts\package.ps1 -Configuration Release -Language en
   ```

### Encrypted cartridge images

The preparation script also supports encrypted retail NCCH v2 images that use slot 0x2C. Install the Python dependency with `python -m pip install cryptography`, then add `-KeyFile "C:\Private\slot0x2c.key"` to the build or preparation command. The key file must contain your local slot 0x2C KeyX as 32 hexadecimal digits. Keep cartridge images, keys, and generated files local.

## Launch the game

Open `dist/NewSuperMarioBros2.exe` in File Explorer, or run the following command in PowerShell from the source folder.

```powershell
.\dist\NewSuperMarioBros2.exe
```

Keep the executable and its companion files together in `dist`. On first launch, choose **Cancel** at the SpotPass prompt and dismiss any follow-up messages to start local solo play.

User data lives under `dist/userdata`. The volume defaults to 25%. With the game closed, set `volume` to a value from 0 to 100 in `dist/userdata/settings.ini`. Vulkan is the default renderer. Set `gpu_renderer=0` in the same file for the software renderer with Direct3D 11 presentation.

The Mii parts and shared font are generated locally by the pinned [system archive tools](https://github.com/B3n30/citra_system_archives/tree/f470e0c9d341db73b8a24880295d2eab4cd81660).

## Default controls

Use the arrow keys or the physical WASD positions (ZQSD on AZERTY) to move. The defaults for 3DS A, B, X and Y are K, J, I and U. Use Enter for Start and click the lower screen for touch input.
