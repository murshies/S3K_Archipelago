@echo off

echo Select your Sonic 3 ROM...
for /f "delims=" %%I in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; $d.Title = 'Select Sonic 3 ROM'; $buttonClicked = $d.ShowDialog(); if ( $buttonClicked -eq 'OK' ) { $d.FileName }"') do set "S3ROM=%%I"

if not defined S3ROM (
   echo No Sonic 3 ROM selected
   pause
   exit /b 1
)
echo Selected: "%S3ROM%"

echo Select your Sonic ^& Knuckles ROM...
for /f "delims=" %%I in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.OpenFileDialog; $d.Title = 'Select Sonic & Knuckles ROM'; $buttonClicked = $d.ShowDialog(); if ( $buttonClicked -eq 'OK' ) { $d.FileName }"') do set "SKROM=%%I"

if not defined SKROM (
   echo No Sonic ^& Knuckles ROM selected
   pause
   exit /b 1
)

echo Selected: "%SKROM%"

copy /b "%SKROM%" + "%S3ROM%" S3K.md
echo Wrote %CD%\S3K.md
pause
