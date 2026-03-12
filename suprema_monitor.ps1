Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Load Windows OCR
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.RandomAccessStream, Windows.Foundation, ContentType=WindowsRuntime]

# Helper to await UWP async
Add-Type -TypeDefinition @"
using System;
using System.Threading.Tasks;
using System.Runtime.CompilerServices;
using Windows.Foundation;
public static class AsyncHelper {
    public static T Await<T>(IAsyncOperation<T> op) {
        return Task.Run(() => op.AsTask()).Result;
    }
}
"@ -ReferencedAssemblies @(
    "System.Runtime.WindowsRuntime",
    [Windows.Media.Ocr.OcrEngine].Assembly.Location,
    [Windows.Graphics.Imaging.SoftwareBitmap].Assembly.Location,
    [Windows.Storage.Streams.RandomAccessStream].Assembly.Location
)

# Get OCR engine
$ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage(
    [Windows.Globalization.Language]::new("pt-BR")
)
if (-not $ocrEngine) {
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
}

# Win32 API for window rect
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Window {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$logFile = "C:\Users\PC\suprema_hands.log"
$lastText = ""
$interval = 1  # seconds

Write-Host "=== SUPREMA MONITOR ===" -ForegroundColor Green
Write-Host "Log: $logFile"
Write-Host "Intervalo: ${interval}s"
Write-Host "Ctrl+C para parar"
Write-Host ""

# Find Suprema window
function Find-SupremaWindow {
    $found = $null
    $callback = [Win32Window+EnumWindowsProc]{
        param($hWnd, $lParam)
        if ([Win32Window]::IsWindowVisible($hWnd)) {
            $sb = New-Object System.Text.StringBuilder 256
            [Win32Window]::GetWindowText($hWnd, $sb, 256) | Out-Null
            $title = $sb.ToString()
            if ($title -match "Suprema|suprema|SUPREMA|FichaNet|fichanet|B2XGroup|Poker") {
                $script:found = $hWnd
                return $false
            }
        }
        return $true
    }
    [Win32Window]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
    return $found
}

function Capture-AndOCR {
    param($hwnd)

    $rect = New-Object Win32Window+RECT
    [Win32Window]::GetWindowRect($hwnd, [ref]$rect) | Out-Null

    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    if ($w -le 0 -or $h -le 0) { return $null }

    # Capture window region
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $gfx = [System.Drawing.Graphics]::FromImage($bmp)
    $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [System.Drawing.Size]::new($w, $h))
    $gfx.Dispose()

    # Save temp for OCR
    $tmpFile = [System.IO.Path]::GetTempFileName() + ".png"
    $bmp.Save($tmpFile, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()

    # OCR via Windows API
    try {
        $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync($tmpFile)
        $file = [AsyncHelper]::Await($file)
        $stream = [AsyncHelper]::Await($file.OpenAsync([Windows.Storage.FileAccessMode]::Read))
        $decoder = [AsyncHelper]::Await([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
        $softBmp = [AsyncHelper]::Await($decoder.GetSoftwareBitmapAsync())
        $result = [AsyncHelper]::Await($ocrEngine.RecognizeAsync($softBmp))
        $text = $result.Text
        $stream.Dispose()
    } catch {
        $text = "[OCR ERROR: $($_.Exception.Message)]"
    }

    # Cleanup temp
    Remove-Item $tmpFile -ErrorAction SilentlyContinue

    return $text
}

$hwnd = Find-SupremaWindow
if (-not $hwnd) {
    Write-Host "Janela Suprema nao encontrada! Tentando tela cheia..." -ForegroundColor Yellow
}

Write-Host "Monitorando... ($(Get-Date -Format 'HH:mm:ss'))" -ForegroundColor Cyan
Add-Content $logFile "`n=== SESSAO INICIADA $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

$frameCount = 0
while ($true) {
    $ts = Get-Date -Format "HH:mm:ss.fff"

    # Re-find window periodically
    if ($frameCount % 10 -eq 0) {
        $newHwnd = Find-SupremaWindow
        if ($newHwnd) { $hwnd = $newHwnd }
    }

    if ($hwnd) {
        $text = Capture-AndOCR $hwnd
    } else {
        # Fallback: full screen
        $bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
        $gfx = [System.Drawing.Graphics]::FromImage($bmp)
        $gfx.CopyFromScreen(0, 0, 0, 0, $bmp.Size)
        $gfx.Dispose()
        $tmpFile = [System.IO.Path]::GetTempFileName() + ".png"
        $bmp.Save($tmpFile)
        $bmp.Dispose()
        $text = "[fullscreen fallback]"
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    }

    # Only log if text changed (saves space, shows transitions)
    if ($text -and $text -ne $lastText) {
        $entry = "[$ts] $text"
        Add-Content $logFile $entry
        Write-Host "[$ts] MUDANCA DETECTADA" -ForegroundColor Yellow
        $diffLen = if ($lastText) { [Math]::Abs($text.Length - $lastText.Length) } else { $text.Length }
        Write-Host "  Chars: $($text.Length) (delta: $diffLen)" -ForegroundColor Gray
        # Show first 200 chars preview
        $preview = if ($text.Length -gt 200) { $text.Substring(0,200) + "..." } else { $text }
        Write-Host "  $preview" -ForegroundColor DarkGray
        $lastText = $text
    }

    $frameCount++
    Start-Sleep -Seconds $interval
}
