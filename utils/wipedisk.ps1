param(
    [int[]] $DiskNumbers = @(10),
    [switch] $WhatIf
)

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must be run as Administrator."
    }
}

function Size-ApproxMatch {
    param(
        [UInt64] $Bytes,
        [UInt64] $TargetBytes,
        [double] $TolerancePct = 3.0
    )
    $low  = [UInt64]($TargetBytes * (1.0 - $TolerancePct/100.0))
    $high = [UInt64]($TargetBytes * (1.0 + $TolerancePct/100.0))
    return ($Bytes -ge $low -and $Bytes -le $high)
}

function Wipe-RepartitionFormatDisk {
    param(
        [int] $DiskNumber,
        [switch] $WhatIf
    )

    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop

    if ($disk.IsBoot -or $disk.IsSystem) {
        throw "Refusing Disk ${DiskNumber}: marked as Boot/System."
    }

    $size = [UInt64]$disk.Size
    $GiB  = [math]::Round($size / 1GB, 1)

    $is512ish = Size-ApproxMatch -Bytes $size -TargetBytes 512GB -TolerancePct 10.0
    $is1Tish  = Size-ApproxMatch -Bytes $size -TargetBytes 1TB   -TolerancePct 10.0
    $is2Tish  = Size-ApproxMatch -Bytes $size -TargetBytes 2TB   -TolerancePct 6.0

    if (-not ($is512ish -or $is1Tish)) {
        Write-Warning "Disk ${DiskNumber}: size ${GiB} GB is not ~512GB or ~1TB. Skipping."
        return
    }
    if ($is2Tish) {
        Write-Warning "Disk ${DiskNumber}: size looks ~2TB (${GiB} GB). Extra safety skip."
        return
    }

    if ($disk.OperationalStatus -contains 'Offline') {
        if ($WhatIf) { Write-Host "WHATIF: Set-Disk -Number ${DiskNumber} -IsOffline `$false" }
        else { Set-Disk -Number $DiskNumber -IsOffline $false }
    }
    if ($disk.IsReadOnly) {
        if ($WhatIf) { Write-Host "WHATIF: Set-Disk -Number ${DiskNumber} -IsReadOnly `$false" }
        else { Set-Disk -Number $DiskNumber -IsReadOnly $false }
    }

    # UPDATED: accept 4 OR 5 partitions
    $parts = Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue
    $partCount = @($parts).Count
    if ($partCount -notin 4,5) {
        Write-Warning "Disk ${DiskNumber}: has ${partCount} partition(s), expected 4 or 5. Skipping."
        return
    }

    Write-Host "Disk ${DiskNumber}: PASSED gates (Size ~512GB/1TB, not ~2TB, ${partCount} partitions). Proceeding..."

    foreach ($p in $parts | Sort-Object PartitionNumber -Descending) {
        if ($WhatIf) {
            Write-Host "WHATIF: Remove-Partition -DiskNumber ${DiskNumber} -PartitionNumber $($p.PartitionNumber) -Confirm:`$false"
        } else {
            Remove-Partition -DiskNumber $DiskNumber -PartitionNumber $p.PartitionNumber -Confirm:$false
        }
    }

    $disk = Get-Disk -Number $DiskNumber
    if ($disk.PartitionStyle -eq 'RAW') {
        if ($WhatIf) { Write-Host "WHATIF: Initialize-Disk -Number ${DiskNumber} -PartitionStyle GPT" }
        else { Initialize-Disk -Number $DiskNumber -PartitionStyle GPT }
    }

    if ($WhatIf) {
        Write-Host "WHATIF: New-Partition -DiskNumber ${DiskNumber} -UseMaximumSize -AssignDriveLetter | Format-Volume -FileSystem NTFS -NewFileSystemLabel '' -Confirm:`$false"
    } else {
        $newPart = New-Partition -DiskNumber $DiskNumber -UseMaximumSize -AssignDriveLetter
        Format-Volume -Partition $newPart -FileSystem NTFS -NewFileSystemLabel "" -Confirm:$false
    }

    Write-Host "Disk ${DiskNumber}: done."
}

Assert-Admin

foreach ($n in $DiskNumbers) {
    try {
        Wipe-RepartitionFormatDisk -DiskNumber $n -WhatIf:$WhatIf
    } catch {
        Write-Warning "Disk ${n}: $($_.Exception.Message)"
    }
}