param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidateSet('PowerPoint.Application','KWPP.Application')][string]$Application = 'PowerPoint.Application',
    [int]$Width = 1800
)
$ErrorActionPreference = 'Stop'
$resolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Use a new output directory; existing files will not be overwritten.' }
$null = New-Item -ItemType Directory -Path $OutputDirectory
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
$presentation = $null
$result = [ordered]@{ application=$Application; rendered=$false; group_test=$null; ungroup_test=$null; saved_changes=$false; error=$null; previews=@() }
try {
    $app = New-Object -ComObject $Application
    # Open an independent untitled copy, without a visible window.
    $presentation = $app.Presentations.Open($resolvedInput, 0, -1, 0)
    $height = [int][Math]::Round($Width * $presentation.PageSetup.SlideHeight / $presentation.PageSetup.SlideWidth)
    for ($i=1; $i -le $presentation.Slides.Count; $i++) {
        $slide = $presentation.Slides.Item($i)
        $png = Join-Path $resolvedOutput ('slide-{0:D2}.png' -f $i)
        $slide.Export($png, 'PNG', $Width, $height)
        $result.previews += $png
    }
    $result.rendered = $true
    $slide = $presentation.Slides.Item(1)
    # Ungroup a single outer figure group before testing the original components.
    if ($slide.Shapes.Count -eq 1 -and $slide.Shapes.Item(1).Type -eq 6) {
        $null = $slide.Shapes.Item(1).Ungroup()
        $result.ungroup_test = $true
    }
    if ($slide.Shapes.Count -ge 2) {
        $count = $slide.Shapes.Count
        $namesBefore = @(for ($j=1; $j -le $count; $j++) { $slide.Shapes.Item($j).Name })
        $indices = [object[]](1..$count)
        $group = $slide.Shapes.Range($indices).Group()
        # WPS may count nested members recursively; compare the actual group and round trip.
        $result.group_test = ($group.Type -eq 6 -and $slide.Shapes.Count -eq 1)
        $null = $group.Ungroup()
        $namesAfter = @(for ($j=1; $j -le $slide.Shapes.Count; $j++) { $slide.Shapes.Item($j).Name })
        $result.ungroup_test = ($slide.Shapes.Count -eq $count -and ($namesBefore -join '|') -eq ($namesAfter -join '|'))
        if (-not $result.group_test -or -not $result.ungroup_test) { throw 'Grouping round trip did not preserve the top-level objects.' }
    }
} catch {
    $result.error = $_.Exception.Message
} finally {
    if ($null -ne $presentation) {
        $presentation.Saved = -1
        $presentation.Close()
    }
    # Do not Quit the application: other user presentations may be open.
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $resolvedOutput 'render-check.json') -Encoding UTF8
}
$result | ConvertTo-Json -Depth 5
if ($null -ne $result.error) { exit 1 }
