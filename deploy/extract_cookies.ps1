# Extract YouTube cookies from Chrome using rookiepy (requires admin for Chrome 130+)
python -c @"
import rookiepy

cookies = rookiepy.chrome(['.youtube.com', '.google.com'])
print(f'Found {len(cookies)} cookies')

output = 'c:\\100star\\merge-video\\cookies.txt'
with open(output, 'w', encoding='utf-8') as f:
    f.write('# Netscape HTTP Cookie File\n')
    f.write('# Extracted via rookiepy\n\n')
    for c in cookies:
        domain = c.get('domain', '')
        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
        path = c.get('path', '/')
        secure = 'TRUE' if c.get('secure', False) else 'FALSE'
        expires = int(c.get('expires', 0))
        name = c.get('name', '')
        value = c.get('value', '')
        f.write(f'{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n')

print(f'Saved to {output}')
"@
pause
