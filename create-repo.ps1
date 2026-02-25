$ErrorActionPreference = "Stop"
gh repo create maximosovsky/merge-video --public --description "Merge video files into one" --source . --remote origin --push
Write-Host "Done"
