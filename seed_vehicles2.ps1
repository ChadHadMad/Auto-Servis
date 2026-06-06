# seed_vehicles2.ps1 — Iveco Daily + Toyota Aygo
$API = "http://localhost:8080/chat-api"
$KEY = "lozinka"
$headers = @{ "Content-Type" = "application/json" }

Write-Host "=== UNOS VOZILA 3 i 4 ===" -ForegroundColor Cyan

# ── Iveco Daily ───────────────────────────────────────────────────────────────
Write-Host "Dodajem Iveco Daily..." -ForegroundColor Yellow

$iveco = '{"vin":"ZCFC65D0005751484","plate":"PU001GT","vehicle":{"make":"Iveco","model":"Daily 2.3 D","year":2008,"engine_cc":2998,"engine_kw":130},"owner":{"name":"TOMC AUTOMEHANIKA D.O.O.","phone":"","email":""}}'

try {
    Invoke-RestMethod -Uri "$API/service-book?admin_key=$KEY" -Method POST -Body $iveco -Headers $headers | Out-Null
    Write-Host "Iveco dodan!" -ForegroundColor Green
} catch {
    Write-Host "Iveco: $($_.Exception.Message)" -ForegroundColor Red
}

$ivecoEntries = @(
    '{"date":"2016-08-23","km":156360,"oil_type":"5W30","extra":"Ulje mjenjaca - Additiv","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":false,"air_filter":false,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":true,"power_steering_fluid":null}}',
    '{"date":"2018-10-17","km":184330,"oil_type":"5W30","extra":"Glava motora s/a, dist-gom, gom.bat glave, zupcastiremen x2","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":true,"micro_belt":true,"brake_fluid":null,"coolant":true,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2020-08-21","km":186400,"oil_type":"","extra":"Set zupcakog+vod.pumpa, alternator, nosac motora, vanjski remen, klizac","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":true,"micro_belt":true,"brake_fluid":null,"coolant":true,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2020-07-30","km":204400,"oil_type":"5W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2020-11-27","km":208969,"oil_type":"","extra":"Zatezaci 2x, semeoring radilice","items":{"oil_filter":null,"cabin_filter":null,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":true,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2022-06-03","km":223400,"oil_type":"3W30","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2024-02-22","km":235391,"oil_type":"5W30","extra":"Elektropo, zglob vilice x4, seleni, balanstampon gumice, nosaci izamine","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":null,"air_filter":null,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2026-01-29","km":239350,"oil_type":"5W30","extra":"Baterija","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":true,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}'
)

Write-Host "Dodajem servisne zapise za Iveco..." -ForegroundColor Yellow
foreach ($entry in $ivecoEntries) {
    try {
        Invoke-RestMethod -Uri "$API/service-book/ZCFC65D0005751484/entries?admin_key=$KEY&recorded_by=import" -Method POST -Body $entry -Headers $headers | Out-Null
        $km = ($entry | ConvertFrom-Json).km
        Write-Host "  OK: $km km" -ForegroundColor Green
    } catch {
        Write-Host "  Greska: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 300
}

# ── Toyota Aygo ───────────────────────────────────────────────────────────────
Write-Host "Dodajem Toyota Aygo..." -ForegroundColor Yellow

$aygo = '{"vin":"JTDKGNEC40N092575","plate":"ZG4850JV","vehicle":{"make":"Toyota","model":"Aygo 1.0 VVTi","year":2015,"engine_cc":998,"engine_kw":51},"owner":{"name":"Krnić Nikolina","phone":"","email":""}}'

try {
    Invoke-RestMethod -Uri "$API/service-book?admin_key=$KEY" -Method POST -Body $aygo -Headers $headers | Out-Null
    Write-Host "Toyota Aygo dodana!" -ForegroundColor Green
} catch {
    Write-Host "Toyota: $($_.Exception.Message)" -ForegroundColor Red
}

$aygoEntries = @(
    '{"date":"2023-05-26","km":82500,"oil_type":"5W40","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":false,"air_filter":false,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2024-05-11","km":97200,"oil_type":"5W40","extra":"Dekarbonizacija","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":false,"air_filter":true,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}',
    '{"date":"2025-08-12","km":108000,"oil_type":"5W40","extra":"","items":{"oil_filter":true,"cabin_filter":true,"fuel_filter":false,"air_filter":false,"spark_plug":null,"toothed_belt":null,"micro_belt":null,"brake_fluid":null,"coolant":null,"gearbox_oil":null,"power_steering_fluid":null}}'
)

Write-Host "Dodajem servisne zapise za Toyota Aygo..." -ForegroundColor Yellow
foreach ($entry in $aygoEntries) {
    try {
        Invoke-RestMethod -Uri "$API/service-book/JTDKGNEC40N092575/entries?admin_key=$KEY&recorded_by=import" -Method POST -Body $entry -Headers $headers | Out-Null
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
