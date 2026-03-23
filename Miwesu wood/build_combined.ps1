$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$files = @(
  "Next.js E-commerce Firewood Project.txt",
  "Researching Firewood Visuals for Website.txt",
  "Signal Engineer Preparation Checklist.txt",
  "WOODS_PAGE_IMAGES_SPEC.txt",
  "Firewood SEO Strategy_ Gauteng Dominance.txt",
  "HOME_PAGE_SUMMARY.txt",
  "miwesu-overview.txt",
  "PROJECT_LOOK_AND_FEEL.txt",
  "Braai Wood Research for E-commerce.txt",
  "Firewood SEO Strategy for Gauteng.txt",
  "Next.js Firewood SEO Strategy Research.txt",
  "Advanced 2026 Ecosystem Research.txt",
  "Braai Wood Ad Strategy Research Plan.txt",
  "Braai Wood Landing Page Research & Design.txt",
  "Facebook Ad Plan for Braai Wood.txt",
  "Facebook Ads and Meta Business Suite.txt",
  "Facebook Ads Strategy for Pretoria.txt",
  "Firewood Reimagined_ Tech Fusion Campaign (1).txt",
  "Firewood Reimagined_ Tech Fusion Campaign.txt",
  "Firewood SEO Strategy_ Gauteng Dominance (1).txt",
  "Mastering 2026 Ad Strategies.txt",
  "Meta Ad Creative Optimization & ROI.txt"
)

$out = "MIWESU_PREMIUM_FIRE_WOOD_KNOWLEDGE_COMBINED.txt"
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("================================================================================
  MIWESU PREMIUM FIRE WOOD - COMBINED KNOWLEDGE BASE (ALL SOURCES)
================================================================================
Branding normalized to Miwesu Premium Fire Wood. Website: https://miwesufirewood.co.za
================================================================================
")

$i = 1
foreach ($f in $files) {
  if (Test-Path $f) {
    $text = Get-Content -Path $f -Raw -Encoding UTF8
    if ($text) {
      $text = $text -replace 'Miwesu Fire Wood','Miwesu Premium Fire Wood'
      $text = $text -replace 'Vaalpenskraal','Miwesu Premium Fire Wood'
      $text = $text -replace 'miwesu\.co\.za','miwesufirewood.co.za'
      [void]$sb.AppendLine("")
      [void]$sb.AppendLine("================================================================================")
      [void]$sb.AppendLine("SOURCE $i : $f")
      [void]$sb.AppendLine("================================================================================")
      [void]$sb.AppendLine("")
      [void]$sb.Append($text)
      [void]$sb.AppendLine("")
      $i++
    }
  }
}

[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot $out), $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
Write-Host "Created $out with $($i - 1) sources."
