/*
 * InfoFileOverlay.cs - Versión Estable (Solo ADS)
 */
using System;
using System.IO;
using System.Runtime.InteropServices;

namespace InfoFileOverlay
{
    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.None)]
    [Guid("A4E23B0E-9B4D-4E6C-A12F-7C6D8E9F0A1B")]
    [ProgId("InfoFile.OverlayIcon")]
    public class InfoFileOverlayHandler : IShellIconOverlayIdentifier
    {
        private static readonly string IconPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "InfoFile", "overlay.ico"
        );

        public int GetOverlayInfo(IntPtr pwszIconFile, int cchMax, out int pIndex, out uint pdwFlags)
        {
            WriteString(pwszIconFile, IconPath, cchMax);
            pIndex = 0;
            pdwFlags = 0x00000001; // ISIOI_ICONFILE
            return 0; // S_OK
        }

        public int GetPriority(out int pIPriority)
        {
            pIPriority = 10; // Prioridad alta
            return 0;
        }

        public int IsMemberOf(string pwszPath, uint dwAttrib)
        {
            try
            {
                string path = Path.GetFullPath(pwszPath);
                string adsPath = path + ":InfoFile";

                if (File.Exists(adsPath))
                {
                    string content = File.ReadAllText(adsPath).Trim();
                    if (!string.IsNullOrWhiteSpace(content))
                        return 0; // Mostrar overlay
                }

                // Soporte para carpetas
                if (Directory.Exists(path))
                {
                    string desktopIni = Path.Combine(path, "desktop.ini");
                    if (File.Exists(desktopIni))
                    {
                        string content = File.ReadAllText(desktopIni);
                        if (content.Contains("InfoTip") || content.Contains("InfoFile"))
                            return 0;
                    }
                }
            }
            catch { }

            return 1; // No mostrar
        }

        private static void WriteString(IntPtr dest, string src, int max)
        {
            int len = Math.Min(src.Length, max - 1);
            for (int i = 0; i < len; i++)
                Marshal.WriteInt16(dest, i * 2, src[i]);
            Marshal.WriteInt16(dest, len * 2, 0);
        }
    }

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("0C6C4200-C589-11D0-999A-00C04FD655E1")]
    public interface IShellIconOverlayIdentifier
    {
        [PreserveSig]
        int GetOverlayInfo(IntPtr pwszIconFile, int cchMax, [Out] out int pIndex, [Out] out uint pdwFlags);
        [PreserveSig]
        int GetPriority([Out] out int pIPriority);
        [PreserveSig]
        int IsMemberOf([MarshalAs(UnmanagedType.LPWStr)] string pwszPath, uint dwAttrib);
    }
}