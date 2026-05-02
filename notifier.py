"""
Windows bildirim modülü.
winotify veya win10toast kullanır, yoksa tkinter fallback.
"""

import subprocess
import sys


def send_notification(title: str, message: str, duration: int = 5):
    """
    Windows toast bildirimi gönderir.
    """
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="Ezan Vakti",
            title=title,
            msg=message,
            duration="short",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return
    except ImportError:
        pass

    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=duration, threaded=True)
        return
    except ImportError:
        pass

    # Fallback: PowerShell ile bildirim
    try:
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
        $text = $xml.GetElementsByTagName('text')
        $text[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null
        $text[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Ezan Vakti').Show($toast)
        """
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=5)
    except Exception:
        pass
