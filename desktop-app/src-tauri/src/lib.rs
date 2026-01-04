use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct IngestionConfig {
    path: Option<String>,
    name: Option<String>,
    source: String,
    tags: Vec<String>,
    license: Option<String>,
    download_strategy: Option<String>,
    output_dir: Option<String>,
}

#[derive(Debug, Serialize, Clone)]
pub struct LogEntry {
    #[serde(rename = "type")]
    log_type: String,
    message: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct IngestionResult {
    success: bool,
    manifest_json: Option<String>,
    error: Option<String>,
}

#[tauri::command]
async fn run_ingestion(
    app: AppHandle,
    config: IngestionConfig,
    ingestion_path: String,
) -> Result<IngestionResult, String> {
    match config.source.as_str() {
        "filesystem" => run_filesystem_ingestion(app, config, ingestion_path).await,
        "fab" | "uas" => run_marketplace_ingestion(app, config, ingestion_path).await,
        _ => Err(format!("Unknown source type: {}", config.source)),
    }
}

async fn run_filesystem_ingestion(
    app: AppHandle,
    config: IngestionConfig,
    ingestion_path: String,
) -> Result<IngestionResult, String> {
    let path = config.path.ok_or("Path is required for filesystem source")?;
    let name = config.name.ok_or("Name is required for filesystem source")?;

    let mut args = vec![
        "run".to_string(),
        "ingest".to_string(),
        "--path".to_string(),
        path,
        "--name".to_string(),
        name,
        "--source".to_string(),
        "filesystem".to_string(),
    ];

    if !config.tags.is_empty() {
        args.push("--tags".to_string());
        args.extend(config.tags.iter().cloned());
    }

    if let Some(license) = &config.license {
        if !license.is_empty() {
            args.push("--license".to_string());
            args.push(license.clone());
        }
    }

    run_uv_command(app, args, ingestion_path).await
}

async fn run_marketplace_ingestion(
    app: AppHandle,
    config: IngestionConfig,
    ingestion_path: String,
) -> Result<IngestionResult, String> {
    let _ = app.emit(
        "ingestion-log",
        LogEntry {
            log_type: "info".to_string(),
            message: format!("Syncing {} dependencies...", config.source),
        },
    );

    run_uv_sync(&app, &ingestion_path, &config.source).await?;

    let mut args = vec![
        "run".to_string(),
        "python".to_string(),
        "-m".to_string(),
        "game_asset_tracker_ingestion.gui_helper".to_string(),
        config.source.clone(),
    ];

    if let Some(strategy) = &config.download_strategy {
        args.push("--download-strategy".to_string());
        args.push(strategy.clone());
    }

    if let Some(output) = &config.output_dir {
        args.push("--output-dir".to_string());
        args.push(output.clone());
    }

    run_uv_command(app, args, ingestion_path).await
}

async fn run_uv_sync(app: &AppHandle, working_dir: &str, extra: &str) -> Result<(), String> {
    let shell = app.shell();
    let args = vec!["sync", "--extra", extra];
    
    let output = shell
        .command("uv")
        .args(&args)
        .current_dir(working_dir)
        .output()
        .await
        .map_err(|e| format!("Failed to run uv sync: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Dependency sync failed: {}", stderr));
    }
    Ok(())
}

async fn run_uv_command(
    app: AppHandle,
    args: Vec<String>,
    working_dir: String,
) -> Result<IngestionResult, String> {
    let shell = app.shell();
    let command = shell
        .command("uv")
        .args(&args)
        .current_dir(&working_dir);

    let (mut rx, _child) = command.spawn().map_err(|e| format!("Failed to spawn: {}", e))?;

    let mut stdout_buffer = String::new();
    let mut stderr_buffer = String::new();

    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => {
                let text = String::from_utf8_lossy(&line).to_string();
                stdout_buffer.push_str(&text);
            }
            CommandEvent::Stderr(line) => {
                let text = String::from_utf8_lossy(&line).to_string();
                stderr_buffer.push_str(&text);
                stderr_buffer.push('\n');
                let _ = app.emit(
                    "ingestion-log",
                    LogEntry {
                        log_type: "stderr".to_string(),
                        message: text,
                    },
                );
            }
            CommandEvent::Terminated(payload) => {
                if payload.code == Some(0) {
                    return Ok(IngestionResult {
                        success: true,
                        manifest_json: Some(stdout_buffer),
                        error: None,
                    });
                } else {
                    return Ok(IngestionResult {
                        success: false,
                        manifest_json: None,
                        error: Some(stderr_buffer),
                    });
                }
            }
            CommandEvent::Error(err) => {
                return Err(format!("Command error: {}", err));
            }
            _ => {}
        }
    }

    Err("Process ended unexpectedly".to_string())
}

#[tauri::command]
fn validate_ingestion_path(path: String) -> Result<bool, String> {
    let pyproject = std::path::Path::new(&path).join("pyproject.toml");
    Ok(pyproject.exists())
}

#[tauri::command]
fn check_source_available(source: String, ingestion_path: String) -> Result<bool, String> {
    match source.as_str() {
        "filesystem" => Ok(true),
        "fab" => {
            let pyproject = std::path::Path::new(&ingestion_path).join("pyproject.toml");
            if !pyproject.exists() {
                return Ok(false);
            }
            Ok(true)
        }
        "uas" => {
            let pyproject = std::path::Path::new(&ingestion_path).join("pyproject.toml");
            if !pyproject.exists() {
                return Ok(false);
            }
            Ok(true)
        }
        _ => Ok(false),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            run_ingestion,
            validate_ingestion_path,
            check_source_available
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
