#!/usr/bin/env pwsh
<##
# File: _tools/continue_run.ps1
# Purpose: Wrapper around the Continue CLI to run a prompt against one or more files.
# It processes each target file, performs template replacement in the prompt ({{file}} -> file path),
# and invokes `cn` once per file.
# Usage examples:
#   ./_tools/continue_run.ps1 -Prompt "Add a summary section with context: {{file}}" -Targets "_book_recipes/001.md"
#   ./_tools/continue_run.ps1 -Prompt "Fix formatting" -Targets "_book_chapters" -AllRecursively
##>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Prompt to send to Continue.")]
    [string]$Prompt,

    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true, HelpMessage = "Files or directories to process.")]
    [string[]]$Targets,

    [switch]$AllRecursively,
    [switch]$r
)

# Resolve all target files. If a target is a directory and -AllRecursively, list all *.md files under it.
$AllFiles = @()
foreach ($t in $Targets) {
    if (Test-Path -Path $t -PathType Container) {
        if ($AllRecursively -or $r) {
            $files = Get-ChildItem -Path $t -Recurse -Filter *.md -File | Select-Object -ExpandProperty FullName
            $AllFiles += $files
        } else {
            Write-Warning "Skipping directory '$t' as -AllRecursively/ -r not specified."
        }
    } elseif (Test-Path -Path $t -PathType Leaf) {
        $AllFiles += (Resolve-Path -LiteralPath $t).ProviderPath
    } else {
        Write-Warning "Target '$t' does not exist."
    }
}

if ($AllFiles.Count -eq 0) {
    Write-Error "No valid files to process. Aborting."
    exit 1
}

# Run Continue on each file
foreach ($file in $AllFiles) {
    if ($PSCmdlet.ShouldProcess($file, 'Run Continue')) {
        Write-Host "Processing: $file" -ForegroundColor Cyan
        try {
            # Perform template replacement. Replace {{file}} with the full path.
            $resolvedPrompt = $Prompt -replace "{{file}}", $file
            # Invoke Continue with the resolved prompt.
            & cn --verbose --prompt $resolvedPrompt "/exit"
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Continue failed on $file with exit code $LASTEXITCODE."
            } else {
                Write-Host "✅ Completed: $file" -ForegroundColor Green
            }
        } catch {
            Write-Error "Error running continue on ${file}: $_"
        }
    }
}

Write-Host "All files processed." -ForegroundColor Yellow
