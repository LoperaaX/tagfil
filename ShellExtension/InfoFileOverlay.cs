/*
 * InfoFileOverlay.cs
 * Shell Extension — IShellIconOverlayIdentifier para InfoFile
 *
 * Muestra un ícono overlay morado sobre archivos/carpetas
 * que tienen descripción en InfoFile.
 *
 * Consulta la DB de SQLite directamente para máxima compatibilidad.
 * Fallback: lee el ADS :InfoFile si SQLite no está disponible.
 */

using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Data.SQLite;

namespace InfoFileOverlay
{
    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.None)]
    [Guid("A4E23B0E-9B4D-4E6C-A12F-7C6D8E9F0A1B")]
    [ProgId("InfoFile.OverlayIcon")]
    public class InfoFileOverlayHandler : IShellIconOverlayIdentifier
    {
        private static readonly string DbPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "InfoFile", "infofile.db"
        );

        private static readonly string IconPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "InfoFile", "overlay.ico"
        );

        // ── IShellIconOverlayIdentifier ──────────────

        public int GetOverlayInfo(
            IntPtr pwszIconFile, int cchMax,
            out int pIndex, out uint pdwFlags)
        {
            WriteString(pwszIconFile, IconPath, cchMax);
            pIndex   = 0;
            pdwFlags = 0x00000001; // ISIOI_ICONFILE
            return 0; // S_OK
        }

        public int GetPriority(out int pIPriority)
        {
            pIPriority = 50;
            return 0;
        }

        public int IsMemberOf(string pwszPath, uint dwAttrib)
        {
            try
            {
                string path = Path.GetFullPath(pwszPath);
                if (HasDescription(path)) return 0;  // S_OK
            }
            catch { }
            return 1; // S_FALSE
        }

        // ── Consulta DB ──────────────────────────────

        private bool HasDescription(string path)
        {
            // Primero intentar SQLite
            if (File.Exists(DbPath))
            {
                try
                {
                    string cs = $"Data Source={DbPath};Version=3;Read Only=True;";
                    using (var conn = new SQLiteConnection(cs))
                    {
                        conn.Open();
                        using (var cmd = conn.CreateCommand())
                        {
                            cmd.CommandText =
                                "SELECT 1 FROM files " +
                                "WHERE path=@p AND description IS NOT NULL " +
                                "AND TRIM(description)!='' LIMIT 1";
                            cmd.Parameters.AddWithValue("@p", path);
                            return cmd.ExecuteScalar() != null;
                        }
                    }
                }
                catch { }
            }

            // Fallback: ADS
            try
            {
                string ads = path + ":InfoFile";
                return File.Exists(ads) &&
                       !string.IsNullOrWhiteSpace(File.ReadAllText(ads));
            }
            catch { return false; }
        }

        // ── Helper ───────────────────────────────────

        private static void WriteString(IntPtr dest, string src, int max)
        {
            int len = Math.Min(src.Length, max - 1);
            for (int i = 0; i < len; i++)
                Marshal.WriteInt16(dest, i * 2, src[i]);
            Marshal.WriteInt16(dest, len * 2, 0);
        }
    }

    // ── Interfaz COM ─────────────────────────────────

    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("0C6C4200-C589-11D0-999A-00C04FD655E1")]
    public interface IShellIconOverlayIdentifier
    {
        [PreserveSig]
        int GetOverlayInfo(IntPtr pwszIconFile, int cchMax,
            [Out] out int pIndex, [Out] out uint pdwFlags);

        [PreserveSig]
        int GetPriority([Out] out int pIPriority);

        [PreserveSig]
        int IsMemberOf([MarshalAs(UnmanagedType.LPWStr)] string pwszPath,
            uint dwAttrib);
    }
}