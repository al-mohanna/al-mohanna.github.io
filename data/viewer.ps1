# نافذة تقرير جمع تلاوات الشيخ د. خالد المهنا – تُحمَّل من المستودع في كل تشغيل
param([string]$Desk = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Add-Type -AssemblyName PresentationFramework
$base = 'https://raw.githubusercontent.com/al-mohanna/al-mohanna.github.io/main/data/'
$csv = Join-Path $Desk 'almuhanna-youtube.csv'

function Ar([string]$s) { $o = ''; foreach ($c in $s.ToCharArray()) { if ($c -ge [char]'0' -and $c -le [char]'9') { $o += [char](0x0660 + [int][string]$c) } else { $o += $c } }; return $o }
function Riyadh([string]$u) { return ([DateTime]::Parse($u, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AdjustToUniversal)).AddHours(3) }

[xml]$x = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="تقرير جمع تلاوات الشيخ خالد المهنا" Width="600" SizeToContent="Height"
        WindowStartupLocation="CenterScreen" FlowDirection="RightToLeft"
        FontFamily="Segoe UI" FontSize="18" Background="#F5F1E6">
  <StackPanel Margin="28,24,28,24">
    <TextBlock Name="Head" FontSize="26" FontWeight="Bold" Foreground="#0B3D2B" TextWrapping="Wrap"/>
    <Border Margin="0,16,0,0" Padding="18,14" Background="#FFFDF7" BorderBrush="#E3D9BF" BorderThickness="1" CornerRadius="14">
      <TextBlock Name="Body" TextWrapping="Wrap" LineHeight="34"/>
    </Border>
    <TextBlock Name="HistT" Margin="0,18,0,4" FontWeight="Bold" Foreground="#0B3D2B" Text="آخر مرات التشغيل"/>
    <TextBlock Name="Hist" TextWrapping="Wrap" LineHeight="30" Foreground="#3B4A42"/>
    <TextBlock Name="Note" Margin="0,12,0,0" TextWrapping="Wrap" Foreground="#A0522D"/>
    <StackPanel Orientation="Horizontal" Margin="0,22,0,0">
      <Button Name="Open" Content="فتح ملف المقاطع" Padding="18,9" Margin="0,0,10,0" Background="#0E4A36" Foreground="White" FontWeight="Bold"/>
      <Button Name="Refresh" Content="تحديث" Padding="18,9" Margin="0,0,10,0"/>
      <Button Name="Close" Content="إغلاق" Padding="18,9"/>
    </StackPanel>
  </StackPanel>
</Window>
'@
$w = [Windows.Markup.XamlReader]::Load((New-Object System.Xml.XmlNodeReader $x))
$BC = New-Object Windows.Media.BrushConverter
$Head = $w.FindName('Head'); $Body = $w.FindName('Body'); $Hist = $w.FindName('Hist'); $Note = $w.FindName('Note')

function Fill {
  $Note.Text = ''
  try {
    $t = '?t=' + [DateTime]::Now.Ticks
    $tmp = Join-Path $env:TEMP 'almuhanna-status.json'
    Invoke-WebRequest -UseBasicParsing -Uri ($base + 'collect_status.json' + $t) -OutFile $tmp
    $st = Get-Content $tmp -Raw -Encoding UTF8 | ConvertFrom-Json
  } catch {
    $Head.Text = 'تعذّر الاتصال'; $Body.Text = 'تأكد من اتصال الإنترنت ثم اضغط «تحديث».'; $Hist.Text = ''; return
  }
  try { Invoke-WebRequest -UseBasicParsing -Uri ($base + 'found.csv' + $t) -OutFile $csv }
  catch { $Note.Text = 'لم يُحدَّث ملف المقاطع. إن كان مفتوحاً في Excel فأغلقه ثم اضغط «تحديث».' }

  if ($st.complete) { $Head.Text = 'اكتمل الجمع ✅'; $Head.Foreground = $BC.ConvertFromString('#14543A') }
  else { $Head.Text = 'الجمع مستمر ولم يكتمل بعد ⏳'; $Head.Foreground = $BC.ConvertFromString('#8A6A1F') }

  $runs = @($st.runs)
  $last = if ($runs.Count) { $runs[$runs.Count - 1] } else { $null }
  $up = (Riyadh $st.updated_utc).ToString('yyyy/MM/dd  hh:mm tt', [Globalization.CultureInfo]::InvariantCulture).Replace('AM', 'ص').Replace('PM', 'م')
  $lines = @()
  $lines += 'عدد المقاطع المجموعة من خارج قناتنا:  ' + (Ar $st.total)
  if ($last) { $lines += 'أُضيف في آخر تشغيل:  ' + (Ar ('+' + $last.added)) + ' مقطعاً' }
  $lines += 'صيغ البحث المنتهية:  ' + (Ar $st.tasks_done) + ' من ' + (Ar $st.tasks_all)
  $lines += 'القنوات التي مرّ عليها كاملة:  ' + (Ar $st.channels_done)
  $lines += 'عدد ليالي الجمع حتى الآن:  ' + (Ar $runs.Count)
  $lines += 'آخر تحديث:  ' + (Ar $up) + '  بتوقيت الرياض'
  if (-not $st.complete) { $lines += 'التشغيل القادم: الليلة الساعة ١:٢٣ — يعمل وحده ولا يحتاج جهازك.' }
  $Body.Text = ($lines -join "`n")

  $h = @()
  for ($i = $runs.Count - 1; $i -ge 0; $i--) {
    $r = $runs[$i]
    $d = (Riyadh $r.at).ToString('yyyy/MM/dd', [Globalization.CultureInfo]::InvariantCulture)
    $h += '•  ' + (Ar $d) + ':  أُضيف ' + (Ar $r.added) + '، والإجمالي ' + (Ar $r.total)
  }
  $Hist.Text = ($h -join "`n")
}

$w.FindName('Open').Add_Click({ if (Test-Path $csv) { Start-Process $csv } else { $Note.Text = 'ملف المقاطع غير موجود بعد. اضغط «تحديث».' } })
$w.FindName('Refresh').Add_Click({ $Head.Text = 'جارٍ التحديث…'; $w.Dispatcher.Invoke([Action]{}, 'Background'); Fill })
$w.FindName('Close').Add_Click({ $w.Close() })
$w.Add_ContentRendered({ Fill })
[void]$w.ShowDialog()
