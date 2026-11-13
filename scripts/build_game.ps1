param(
    [string] $Cartridge,
    [string] $KeyFile,
    [ValidateSet('Release','Debug')] [string] $Configuration = 'Release',
    [ValidateSet('en','fr','de','it','es','nl','pt','ru')] [string] $Language
)
. "$PSScriptRoot/common.ps1"
& "$PSScriptRoot/prepare.ps1" -Cartridge $Cartridge -KeyFile $KeyFile
if ($Configuration -eq 'Debug') { Build-Nsmb2 Debug ON }
else { Build-Nsmb2 Release OFF }
& "$PSScriptRoot/run_tests.ps1" -Configuration $Configuration
$packageOptions = @{ Configuration = $Configuration }
if ($Language) { $packageOptions.Language = $Language }
& "$PSScriptRoot/package.ps1" @packageOptions

