using System;
using System.Diagnostics;
using System.IO;
using System.ServiceProcess;
using System.Threading;

public class BaseRhService : ServiceBase
{
    private Process _process;
    private static readonly string AppDir = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string PythonExe = Path.Combine(AppDir, @"venv\Scripts\python.exe");
    private static readonly string ScriptFile = Path.Combine(AppDir, "app.py");
    private static readonly string LogFile = Path.Combine(AppDir, "service_log.txt");
    private static readonly object LogLock = new object();

    public BaseRhService()
    {
        this.ServiceName = "BaseRhService";
        this.CanStop = true;
        this.CanShutdown = true;
    }

    private static void WriteLog(string message)
    {
        try
        {
            lock (LogLock)
            {
                File.AppendAllText(LogFile, string.Format("{0:yyyy-MM-dd HH:mm:ss} - {1}\r\n", DateTime.Now, message));
            }
        }
        catch {}
    }

    protected override void OnStart(string[] args)
    {
        WriteLog("Serviço BaseRhService iniciando...");
        Thread startThread = new Thread(StartServer);
        startThread.IsBackground = true;
        startThread.Start();
    }

    private void StartServer()
    {
        try
        {
            WriteLog("Aguardando 10 segundos antes de iniciar o servidor Flask...");
            Thread.Sleep(10000);

            KillExistingProcessesOnPort(5062);

            if (!File.Exists(PythonExe))
            {
                WriteLog("ERRO: Python não encontrado em: " + PythonExe);
                return;
            }

            if (!File.Exists(ScriptFile))
            {
                WriteLog("ERRO: Script do app não encontrado em: " + ScriptFile);
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = PythonExe,
                Arguments = string.Format("\"{0}\"", ScriptFile),
                WorkingDirectory = AppDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            psi.EnvironmentVariables["VIRTUAL_ENV"] = Path.Combine(AppDir, "venv");
            psi.EnvironmentVariables["PATH"] = Path.Combine(AppDir, @"venv\Scripts") + ";" + Environment.GetEnvironmentVariable("PATH");
            psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";

            _process = new Process { StartInfo = psi };

            _process.OutputDataReceived += (sender, e) => {
                if (e.Data != null) WriteLog("[FLASK-OUT] " + e.Data);
            };

            _process.ErrorDataReceived += (sender, e) => {
                if (e.Data != null) WriteLog("[FLASK-ERR] " + e.Data);
            };

            WriteLog("Iniciando processo Python...");
            _process.Start();
            _process.BeginOutputReadLine();
            _process.BeginErrorReadLine();

            WriteLog("Processo Python iniciado com PID: " + _process.Id);
            _process.WaitForExit();
            WriteLog("Processo Python encerrou com código de saída: " + _process.ExitCode);
        }
        catch (Exception ex)
        {
            WriteLog("EXCEÇÃO ao iniciar servidor: " + ex.Message + "\r\n" + ex.StackTrace);
        }
    }

    protected override void OnStop()
    {
        WriteLog("Serviço BaseRhService parando...");
        StopServer();
    }

    protected override void OnShutdown()
    {
        WriteLog("Sistema desligando. Serviço BaseRhService parando...");
        StopServer();
    }

    private void StopServer()
    {
        try
        {
            if (_process != null && !_process.HasExited)
            {
                WriteLog("Finalizando processo Flask (PID: " + _process.Id + ")...");
                _process.Kill();
            }
        }
        catch (Exception ex)
        {
            WriteLog("Erro ao dar Kill no processo: " + ex.Message);
        }

        KillExistingProcessesOnPort(5062);
        WriteLog("Serviço BaseRhService parado com sucesso.");
    }

    private void KillExistingProcessesOnPort(int port)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = string.Format("/c \"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr \":{0} \"') do taskkill /PID %a /F\"", port),
                CreateNoWindow = true,
                UseShellExecute = false
            };
            using (Process p = Process.Start(psi))
            {
                p.WaitForExit();
            }
            WriteLog("Busca e encerramento de processos na porta " + port + " executados.");
        }
        catch (Exception ex)
        {
            WriteLog("Erro ao liberar porta " + port + ": " + ex.Message);
        }
    }

    public static void Main()
    {
        ServiceBase.Run(new BaseRhService());
    }
}
