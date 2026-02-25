# Deploy merge-video to Alibaba ECS
# Converts setup.sh to LF and pipes via SSH
# Requires: SSH key auth configured (see deploy/harden.sh)

$server = "root@47.84.36.115"
$scriptPath = "c:\100star\merge-video\deploy\remote-setup.sh"
$content = [System.IO.File]::ReadAllText($scriptPath)
$lfContent = $content -replace "`r`n", "`n"

# Write temp file with Unix line endings
$tempFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tempFile, $lfContent, [System.Text.UTF8Encoding]::new($false))

Write-Host "Deploying to $server..."

# Pipe converted script to SSH (key-based auth)
Get-Content $tempFile -Raw | ssh -o StrictHostKeyChecking=no $server "bash -s"

Remove-Item $tempFile -Force
