$body = @{
    urls = @("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    title = "Test"
    user_id = "web"
} | ConvertTo-Json

$r = Invoke-WebRequest -Uri "http://localhost:8000/merge" -Method POST -ContentType "application/json" -Body $body -ErrorAction Stop
Write-Host "Status: $($r.StatusCode)"
Write-Host $r.Content
