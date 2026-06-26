# =====================================================================
# SOA/SOS - Rotina de push do Folder Vivo para o GitHub (AUTOMATICA)
# Envia index.html + Fatos_Regulatorios_Folder_SOA.json ao repo via
# GitHub Contents API, no branch que o GitHub Pages serve (principal).
# Idempotente por arquivo: so faz commit do que mudou.
# O token vem da variavel de ambiente SOA_GH_TOKEN (NUNCA fica no script).
# =====================================================================
$ErrorActionPreference = "Stop"

# --- Configuracao ---
$owner  = "trigocom-code"
$repo   = "financiamento-de-usinas"
$branch = "principal"                  # <-- branch servido pelo GitHub Pages
$base   = "C:\Users\Henrique Limonta\OneDrive\Documents\Claude\Projects\SOA\SOS — Business Development"
$logFile = Join-Path $base "push_fatos_github.log"

# Arquivos a sincronizar (caminho no repo  =  arquivo local)
$files = @(
  @{ path = "index.html";                          local = (Join-Path $base "index.html") },
  @{ path = "Fatos_Regulatorios_Folder_SOA.json";  local = (Join-Path $base "Fatos_Regulatorios_Folder_SOA.json") }
)
# --------------------

function Log($msg){ $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"; Add-Content -Path $logFile -Value $line -Encoding UTF8; Write-Output $line }

function Push-File($headers, $apiUrl, $localFile, $path) {
  if (-not (Test-Path $localFile)) { Log "AVISO: arquivo local nao encontrado, pulando: $localFile"; return }

  $bytes      = [System.IO.File]::ReadAllBytes($localFile)
  $contentB64 = [System.Convert]::ToBase64String($bytes)

  $sha = $null
  try {
    $cur = Invoke-RestMethod -Method GET -Uri "$apiUrl`?ref=$branch" -Headers $headers
    $sha = $cur.sha
    $curB64 = ($cur.content -replace "`r","" -replace "`n","")
    if ($curB64 -eq $contentB64) { Log "Sem mudanca em $path - nada a enviar."; return }
  } catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 404) { $sha = $null }
    else { throw }
  }

  $bodyObj = @{ message = "Atualiza $path ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"; content = $contentB64; branch = $branch }
  if ($sha) { $bodyObj.sha = $sha }
  $body = $bodyObj | ConvertTo-Json -Depth 5

  $resp = Invoke-RestMethod -Method PUT -Uri $apiUrl -Headers $headers -Body $body -ContentType "application/json"
  Log "PUSH OK ($path) - commit $($resp.commit.sha)"
}

try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

  $token = $env:SOA_GH_TOKEN
  if ([string]::IsNullOrWhiteSpace($token)) { Log "ERRO: variavel SOA_GH_TOKEN nao definida. Rode o instalador uma vez."; exit 1 }

  $headers = @{ Authorization = "Bearer $token"; "User-Agent" = "soa-folder-bot"; Accept = "application/vnd.github+json" }

  foreach ($f in $files) {
    $apiUrl = "https://api.github.com/repos/$owner/$repo/contents/$($f.path)"
    Push-File $headers $apiUrl $f.local $f.path
  }
  exit 0
}
catch {
  Log "ERRO: $($_.Exception.Message)"
  exit 1
}
