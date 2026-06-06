# seed_vehicles.ps1
$API = "http://localhost:8080/chat-api"
$KEY = "lozinka"
$headers = @{ "Content-Type" = "application/json" }

Write-Host "=== UNOS VOZILA ===" -ForegroundColor Cyan

# ── VW Golf ──────────────────────────────────────────────────────────────────
Write-Host "Dodajem VW Golf..." -ForegroundColor Yellow

$golf = '{"vin":"WVW1234567890001","plate":"PU797D","vehicle":{"make":"Volkswagen","model":"Golf","year":2018,"engine_cc":1968,"engine_kw":110},"owner":{"name":"TOMC AUTOMEHANIKA D.O.O.","phone":"","email":""}}'

try {
    Invoke-RestMethod -Uri "$API/service-book?admin_key=$KEY" -Method POST -Body $golf -Headers $headers | Out-Null
    Write-Host "Golf dodan!" -ForegroundColor Green
} catch {
    Write-Host "Golf: $($_.Exception.Message)" -ForegroundColor Red
}

$golfEntries = @(
    '{"date":"2024-12-10","km":96700,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"air_filter":true,"fuel_filter":false,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2025-08-02","km":112500,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2025-11-28","km":118150,"oil_type":"","extra":"Prednji diskovi i plocice","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2026-03-05","km":126600,"oil_type":"5W30","extra":"Servis DSG-a, diferencijala i Haldex spojke","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":false,"air_filter":false,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":true,"power_steering_fluid":null}}'
)

foreach ($entry in $golfEntries) {
    try {
        Invoke-RestMethod -Uri "$API/service-book/WVW1234567890001/entries?admin_key=$KEY&recorded_by=import" -Method POST -Body $entry -Headers $headers | Out-Null
        $km = ($entry | ConvertFrom-Json).km
        Write-Host "  OK: $km km" -ForegroundColor Green
    } catch {
        Write-Host "  Greska: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 300
}

# ── Renault Trafic ────────────────────────────────────────────────────────────
Write-Host "Dodajem Renault Trafic..." -ForegroundColor Yellow

$trafic = '{"vin":"VF1FLCA65V248354","plate":"PU500PR","vehicle":{"make":"Renault","model":"Trafic 1.9 DCI","year":2005,"engine_cc":1870,"engine_kw":74},"owner":{"name":"TOMC AUTOMEHANIKA D.O.O.","phone":"","email":""}}'

try {
    Invoke-RestMethod -Uri "$API/service-book?admin_key=$KEY" -Method POST -Body $trafic -Headers $headers | Out-Null
    Write-Host "Trafic dodan!" -ForegroundColor Green
} catch {
    Write-Host "Trafic: $($_.Exception.Message)" -ForegroundColor Red
}

$traficEntries = @(
    '{"date":"2014-12-17","km":114600,"oil_type":"5W40","extra":"Novi donji","items":{"oil_filter":true,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2016-05-04","km":134400,"oil_type":"5W40","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2017-05-04","km":146800,"oil_type":"1W40","extra":"Brtva kartera","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2017-09-01","km":157200,"oil_type":"5W40","extra":"Prednji diskovi i plocice","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2018-05-17","km":171700,"oil_type":"5W40","extra":"","items":{"oil_filter":true,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2021-11-09","km":203400,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2022-06-17","km":182800,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2023-03-21","km":218900,"oil_type":"5W40","extra":"Gumice celjusti lijeve prednje","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2024-05-10","km":230000,"oil_type":"5W40","extra":"Zglob vilice 2x, seleni vilice 4x, seleni mosta 2x","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2024-10-08","km":236300,"oil_type":"","extra":"Protocomer, MAP senzor","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2025-01-27","km":237400,"oil_type":"","extra":"Hladnjak vode","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2026-01-28","km":246000,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}'
)

foreach ($entry in $traficEntries) {
    try {
        Invoke-RestMethod -Uri "$API/service-book/VF1FLCA65V248354/entries?admin_key=$KEY&recorded_by=import" -Method POST -Body $entry -Headers $headers | Out-Null
        $km = ($entry | ConvertFrom-Json).km
        Write-Host "  OK: $km km" -ForegroundColor Green
    } catch {
        Write-Host "  Greska: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 300
}

Write-Host "=== GOTOVO ===" -ForegroundColor Cyan
Write-Host "service-book: http://localhost:8080/service-book.html"
Write-Host "ML dashboard: http://localhost:8080/ml-dashboard.html"
