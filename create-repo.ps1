# Create GitHub repo and push
$ErrorActionPreference = "Stop"

# Create repo via GitHub CLI
gh repo create maximosovsky/merge-video --public --description "Merge video files into one — upload local files or paste YouTube URLs" --source . --remote origin --push

Write-Host "Done! Repo created and pushed."
