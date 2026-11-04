param(
    [string]$Schema = "rime_ice",
    # Input language of the schema's candidates: zh, ja, en, ...
    [string]$Source = "zh",
    # Target languages, comma-separated.
    [string]$Targets = "en,ja",
    [string]$RimeDir = $(Join-Path $env:APPDATA "Rime")
)

$ErrorActionPreference = "Stop"
$labels = @{ en = "英"; ja = "日"; zh = "中"; ko = "韩"; fr = "法"; de = "德"; es = "西"; ru = "俄" }
$targetList = @($Targets.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
if ($targetList.Count -eq 0 -or $targetList -contains $Source) {
    throw "-Targets needs at least one language other than -Source"
}
$options = @("gloss_off") + ($targetList | ForEach-Object { "gloss_$_" })
$states = @("释义关") + ($targetList | ForEach-Object { if ($labels.ContainsKey($_)) { $labels[$_] } else { $_ } })
if ($targetList.Count -gt 1) {
    $options += "gloss_all"
    $states += "全部"
}
$snippet = @"
  engine/filters/@next: lua_filter@rime_gloss_filter
  switches/@next: {options: [$($options -join ', ')], states: [$($states -join ', ')], reset: 1}
  rime_gloss/source: $Source
  rime_gloss/targets: [$($targetList -join ', ')]

"@

New-Item -ItemType Directory -Force -Path $RimeDir | Out-Null
$target = Join-Path $RimeDir "$Schema.custom.yaml"
$utf8 = New-Object System.Text.UTF8Encoding $false
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
    [System.IO.File]::WriteAllText($target, $text + $snippet, $utf8)
    Write-Host "appended gloss patch: $target"
} else {
    [System.IO.File]::WriteAllText($target, "# encoding: utf-8`npatch:`n" + $snippet, $utf8)
    Write-Host "created: $target"
}

Write-Host "重新部署 Rime 后，在方案菜单切换释义开关。"
