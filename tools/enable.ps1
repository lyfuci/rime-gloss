param(
    [string]$Schema = "rime_ice",
    [string]$RimeDir = $(Join-Path $env:APPDATA "Rime")
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $RimeDir | Out-Null
$target = Join-Path $RimeDir "$Schema.custom.yaml"
$snippet = @"
  engine/filters/@next: lua_filter@rime_gloss_filter
  switches/@next: {options: [gloss_off, gloss_en, gloss_ja, gloss_both], states: [释义关, 英, 日, 双语], reset: 1}
  rime_gloss/default: en

"@

if (Test-Path -LiteralPath $target) {
    $text = [System.IO.File]::ReadAllText($target)
    if ($text -match "rime_gloss_filter") {
        Write-Host "already enabled: $target"
        exit 0
    }
    if ($text -notmatch "(?m)^patch:\s*$") {
        throw "$target has no top-level patch:; not modified"
    }
    if (-not $text.EndsWith("`n")) {
        $text += "`n"
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($target, $text + $snippet, $utf8)
    Write-Host "appended gloss patch: $target"
} else {
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $body = "# encoding: utf-8`npatch:`n" + $snippet
    [System.IO.File]::WriteAllText($target, $body, $utf8)
    Write-Host "created: $target"
}

Write-Host "重新部署 Rime 后，在方案菜单切换 释义关 / 英 / 日 / 双语。"
