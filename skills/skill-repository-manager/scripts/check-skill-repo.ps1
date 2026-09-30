[CmdletBinding()]
param(
    [string]$Repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string]$CodexSkills = (Join-Path $env:USERPROFILE '.codex\skills'),
    [switch]$Json,
    [switch]$FailOnDrift,
    [string[]]$LocalConfigPaths = @('references/local-settings.md')
)

$ErrorActionPreference = 'Stop'

$sourceRoot = Join-Path $Repository 'skills'
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "源仓库 skills 目录不存在：$sourceRoot"
}

function Get-SkillFiles([string]$Root) {
    $files = @{}
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return $files }
    # 不进入虚拟环境或缓存目录，避免读取大量依赖文件。
    $pending = [System.Collections.Generic.Stack[object]]::new()
    $pending.Push([PSCustomObject]@{ Path = $Root; Relative = '' })
    while ($pending.Count -gt 0) {
        $current = $pending.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $current.Path -Force) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            $relative = if ($current.Relative) { "$($current.Relative)/$($item.Name)" } else { $item.Name }
            if ($item.PSIsContainer) {
                if ($item.Name -notin @('__pycache__', '.venv', 'venv', '.git', '.pytest_cache', '.ruff_cache')) {
                    $pending.Push([PSCustomObject]@{ Path = $item.FullName; Relative = $relative })
                }
                continue
            }
            if ($item.Name -match '\.(pyc|pyo|log|tmp)$' -or
                $item.Name -in @('option.yml', 'selected_id.txt', '.env', 'LOCAL.md')) { continue }
            $files[$relative] = $item.FullName
        }
    }
    return $files
}

$localPaths = @($LocalConfigPaths | ForEach-Object { $_.Replace('\', '/') })
$sourceSkills = @(Get-ChildItem -LiteralPath $sourceRoot -Directory | Sort-Object Name)
$results = @(foreach ($skill in $sourceSkills) {
    $installedRoot = Join-Path $CodexSkills $skill.Name
    $sourceFiles = Get-SkillFiles $skill.FullName
    $installedFiles = Get-SkillFiles $installedRoot
    $missing = @()
    $changed = @()
    $extra = @()
    $localDifferences = @()
    foreach ($relative in @($sourceFiles.Keys | Sort-Object)) {
        if (-not $installedFiles.ContainsKey($relative)) {
            $missing += $relative
        } elseif ((Get-FileHash -LiteralPath $sourceFiles[$relative] -Algorithm SHA256).Hash -ne
                  (Get-FileHash -LiteralPath $installedFiles[$relative] -Algorithm SHA256).Hash) {
            if ($relative -in $localPaths) { $localDifferences += $relative }
            else { $changed += $relative }
        }
    }
    foreach ($relative in @($installedFiles.Keys | Sort-Object)) {
        if (-not $sourceFiles.ContainsKey($relative)) { $extra += $relative }
    }
    $hasEntry = Test-Path -LiteralPath (Join-Path $skill.FullName 'SKILL.md') -PathType Leaf
    $installed = Test-Path -LiteralPath $installedRoot -PathType Container
    [PSCustomObject]@{
        Name = $skill.Name
        HasSkillMd = $hasEntry
        Installed = $installed
        InSync = ($hasEntry -and $installed -and ($missing.Count + $changed.Count + $extra.Count -eq 0))
        MissingFiles = @($missing)
        ChangedFiles = @($changed)
        ExtraFiles = @($extra)
        LocalConfigDifferences = @($localDifferences)
    }
})
$unmanaged = @(if (Test-Path -LiteralPath $CodexSkills -PathType Container) {
    Get-ChildItem -LiteralPath $CodexSkills -Directory |
        Where-Object { $_.Name -ne '.system' -and $_.Name -notin $sourceSkills.Name } |
        Sort-Object Name | Select-Object -ExpandProperty Name
})

if ($Json) {
    [PSCustomObject]@{ Skills = @($results); UnmanagedSkills = @($unmanaged) } |
        ConvertTo-Json -Depth 5
} else {
    Write-Output "源仓库：$Repository"
    Write-Output "Codex Skills：$CodexSkills"
    Write-Output '【Git 状态】'
    git -C $Repository status --short --branch
    if ($LASTEXITCODE -ne 0) { throw '无法读取 Git 状态' }
    Write-Output '【Git 远程】'
    git -C $Repository remote -v
    if ($LASTEXITCODE -ne 0) { throw '无法读取 Git 远程' }
    Write-Output '【安装副本 SHA256 检查】'
    $results | Select-Object Name, HasSkillMd, Installed, InSync | Format-Table -AutoSize
    foreach ($result in $results) {
        foreach ($field in @('MissingFiles', 'ChangedFiles', 'ExtraFiles', 'LocalConfigDifferences')) {
            foreach ($relative in $result.$field) {
                Write-Output "[$field] $($result.Name)/$relative"
            }
        }
    }
    if ($unmanaged.Count) { Write-Output "独立安装、不参与同步判断：$($unmanaged -join ', ')" }
}
if ($FailOnDrift -and @($results | Where-Object { -not $_.InSync }).Count) { exit 1 }
