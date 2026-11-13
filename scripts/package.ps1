param(
    [ValidateSet('Release','Debug')] [string] $Configuration = 'Release',
    [ValidateSet('en','fr','de','it','es','nl','pt','ru')] [string] $Language
)
. "$PSScriptRoot/common.ps1"
Push-Location -LiteralPath $ProjectRoot
try {
    New-Item -ItemType Directory -Path dist,dist/licenses -Force | Out-Null
    Copy-Item -LiteralPath "build/windows-$Configuration/NewSuperMarioBros2.exe",
        "build/windows-$Configuration/SDL3.dll", 'extracted/NSMB2-EUR.cxi',
        'extracted/mii.romfs', 'extracted/shared-font.bcfnt' -Destination dist -Force
    Copy-Item -LiteralPath 'licenses/Clockwork.txt' -Destination dist/licenses -Force
    Copy-Item -LiteralPath 'build/upstream/SDL3-3.4.0/LICENSE.txt' -Destination dist/licenses/SDL.txt -Force

    Copy-Item -LiteralPath 'licenses/LuigisMansion2Recompiled.txt' -Destination dist/licenses -Force
    Copy-Item -LiteralPath 'build/upstream/xbyak-df112862583c2d327c1d9782fd28f53aa675f11d/COPYRIGHT' -Destination dist/licenses/Xbyak.txt -Force
    $systemLicense = 'build/upstream/citra_system_archives-f470e0c9d341db73b8a24880295d2eab4cd81660/license.txt'
    Copy-Item -LiteralPath $systemLicense -Destination dist/licenses/SystemArchives.txt -Force
    if ($Language) {
        $languageIds = @{ en = 1; fr = 2; de = 3; it = 4; es = 5; nl = 8; pt = 9; ru = 10 }
        $settings = Join-Path $ProjectRoot 'dist/userdata/settings.ini'
        New-Item -ItemType Directory -Path (Split-Path -Parent $settings) -Force | Out-Null
        $lines = @()
        if (Test-Path -LiteralPath $settings) {
            $lines = [IO.File]::ReadAllLines($settings) -notmatch '^language='
        }
        [IO.File]::WriteAllLines($settings, [string[]]($lines + "language=$($languageIds[$Language])"))
        Write-Host "Game language: $($Language.ToLowerInvariant())"
    }
    Write-Host "Windows build: $ProjectRoot\dist\NewSuperMarioBros2.exe"
} finally {
    Pop-Location
}



