[CmdletBinding()]
param(
    [string]$Repository = 'D:\ai-skill\skill',
    [string]$CodexSkills = 'C:\Users\lv\.codex\skills'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Repository -PathType Container)) {
    throw "源仓库不存在：$Repository"
}

Write-Output "源仓库：$Repository"
Write-Output "Codex Skills：$CodexSkills"
Write-Output ''

Write-Output '【Git 状态】'
git -C $Repository status --short --branch
Write-Output ''

Write-Output '【Git 远程】'
git -C $Repository remote -v
Write-Output ''

Write-Output '【源仓库 Skills】'
$sourceSkills = Get-ChildItem -LiteralPath (Join-Path $Repository 'skills') -Directory -ErrorAction SilentlyContinue
foreach ($skill in $sourceSkills) {
    $entry = Join-Path $skill.FullName 'SKILL.md'
    [PSCustomObject]@{
        Name = $skill.Name
        HasSkillMd = Test-Path -LiteralPath $entry -PathType Leaf
        Installed = Test-Path -LiteralPath (Join-Path $CodexSkills $skill.Name) -PathType Container
    }
}
