#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    env,
    fs,
    io::{Read, Write},
    path::PathBuf,
    sync::{Arc, Mutex},
    thread,
};
use url::Url;

#[derive(Serialize, Deserialize, Clone, Debug)]
struct MagnetManifest {
    publisher: String,
    url: String,
    sha256: String,
    size: u64,
}

#[derive(Clone)]
enum Task {
    Idle,
    ComputingHash,
    SavingManifest,
    LoadingManifest,
    Downloading,
    Verifying,
    SavingFile,
    Launching,
    Error(String),
    Success(String),
}

impl Default for Task {
    fn default() -> Self {
        Task::Idle
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Page {
    Create,
    Install,
}

#[derive(Default)]
struct SharedState {
    // Create tab state
    chosen_file: Option<PathBuf>,
    publisher: String,
    url: String,
    computed_sha256: String,
    computed_size: u64,

    // Install tab state
    manifest_path: Option<PathBuf>,
    loaded_manifest: Option<MagnetManifest>,
    auto_launch: bool,

    // Generic
    task: Task,
    current_page: Option<Page>,
}

#[derive(Clone)]
struct App {
    state: Arc<Mutex<SharedState>>,
}

impl App {
    fn new(_: &eframe::CreationContext<'_>) -> Self {
        let mut state = SharedState::default();
        
        // Check if a .mgn file was passed as argument
        let args: Vec<String> = env::args().collect();
        if args.len() > 1 {
            let path = PathBuf::from(&args[1]);
            if path.extension().and_then(|s| s.to_str()) == Some("mgn") {
                state.current_page = Some(Page::Install);
                // Will load the manifest in the first update
                state.manifest_path = Some(path);
            }
        }
        
        Self {
            state: Arc::new(Mutex::new(state)),
        }
    }

    // Helper: compute hash & size on background thread
    fn compute_hash_background(&self, path: PathBuf) {
        let s = self.state.clone();
        thread::spawn(move || {
            {
                let mut st = s.lock().unwrap();
                st.task = Task::ComputingHash;
            }
            let mut file = match fs::File::open(&path) {
                Ok(f) => f,
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Failed open file: {}", e));
                    return;
                }
            };
            let mut hasher = Sha256::new();
            let mut buf = [0u8; 64 * 1024];
            let mut total = 0u64;
            loop {
                match file.read(&mut buf) {
                    Ok(0) => break,
                    Ok(n) => {
                        hasher.update(&buf[..n]);
                        total += n as u64;
                    }
                    Err(e) => {
                        let mut st = s.lock().unwrap();
                        st.task = Task::Error(format!("Read error: {}", e));
                        return;
                    }
                }
            }
            let hash = hex::encode(hasher.finalize());
            let mut st = s.lock().unwrap();
            st.computed_sha256 = hash;
            st.computed_size = total;
            st.task = Task::Idle;
            st.chosen_file = Some(path);
        });
    }

    // Save manifest (background)
    fn save_manifest_background(&self, out_path: PathBuf) {
        let s = self.state.clone();
        thread::spawn(move || {
            let manifest_opt = {
                let st = s.lock().unwrap();
                if st.computed_sha256.is_empty() || st.computed_size == 0 {
                    None
                } else {
                    Some(MagnetManifest {
                        publisher: st.publisher.clone(),
                        url: st.url.clone(),
                        sha256: st.computed_sha256.clone(),
                        size: st.computed_size,
                    })
                }
            };

            match manifest_opt {
                None => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error("Compute SHA256 first and fill fields".into());
                    return;
                }
                Some(manifest) => {
                    {
                        let mut st = s.lock().unwrap();
                        st.task = Task::SavingManifest;
                    }
                    match serde_json::to_string_pretty(&manifest) {
                        Ok(json) => {
                            if let Err(e) = fs::write(&out_path, json) {
                                let mut st = s.lock().unwrap();
                                st.task = Task::Error(format!("Failed to write manifest: {}", e));
                                return;
                            }
                            let mut st = s.lock().unwrap();
                            st.task = Task::Success(format!("Saved manifest: {}", out_path.display()));
                            // Reset fields after successful save
                            st.chosen_file = None;
                            st.publisher.clear();
                            st.url.clear();
                            st.computed_sha256.clear();
                            st.computed_size = 0;
                        }
                        Err(e) => {
                            let mut st = s.lock().unwrap();
                            st.task = Task::Error(format!("JSON error: {}", e));
                        }
                    }
                }
            }
        });
    }

    // Load manifest (background)
    fn load_manifest_background(&self, path: PathBuf) {
        let s = self.state.clone();
        thread::spawn(move || {
            {
                let mut st = s.lock().unwrap();
                st.task = Task::LoadingManifest;
            }
            match fs::read_to_string(&path) {
                Ok(txt) => match serde_json::from_str::<MagnetManifest>(&txt) {
                    Ok(manifest) => {
                        let mut st = s.lock().unwrap();
                        st.loaded_manifest = Some(manifest);
                        st.manifest_path = Some(path);
                        st.task = Task::Idle;
                    }
                    Err(e) => {
                        let mut st = s.lock().unwrap();
                        st.task = Task::Error(format!("Invalid manifest JSON: {}", e));
                    }
                },
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Failed to read manifest: {}", e));
                }
            }
        });
    }

    // Download & verify (background)
    fn download_and_verify_background(&self, auto_launch: bool) {
        let s = self.state.clone();
        thread::spawn(move || {
            {
                let mut st = s.lock().unwrap();
                st.task = Task::Downloading;
            }

            // Clone manifest to work with
            let manifest = {
                let st = s.lock().unwrap();
                if let Some(m) = st.loaded_manifest.clone() {
                    m
                } else {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error("No manifest loaded".into());
                    return;
                }
            };

            // Validate URL and scheme
            let parsed = match Url::parse(&manifest.url) {
                Ok(u) => u,
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Invalid URL: {}", e));
                    return;
                }
            };
            if parsed.scheme() != "https" {
                let mut st = s.lock().unwrap();
                st.task = Task::Error("URL must use HTTPS".into());
                return;
            }

            // Download using reqwest blocking
            let client = match reqwest::blocking::Client::builder().use_rustls_tls().build() {
                Ok(c) => c,
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("HTTP client init failed: {}", e));
                    return;
                }
            };

            let mut resp = match client.get(manifest.url.clone()).send() {
                Ok(r) => r,
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Download failed: {}", e));
                    return;
                }
            };

            if !resp.status().is_success() {
                let mut st = s.lock().unwrap();
                st.task = Task::Error(format!("Server returned status: {}", resp.status()));
                return;
            }

            // Read in chunks, compute hash, store bytes
            {
                let mut st = s.lock().unwrap();
                st.task = Task::Verifying;
            }

            let mut hasher = Sha256::new();
            let mut buffer = Vec::new();
            let mut tmp = [0u8; 64 * 1024];
            let mut total_read = 0usize;
            
            loop {
                match resp.read(&mut tmp) {
                    Ok(0) => break,
                    Ok(n) => {
                        hasher.update(&tmp[..n]);
                        buffer.extend_from_slice(&tmp[..n]);
                        total_read += n;
                    }
                    Err(e) => {
                        let mut st = s.lock().unwrap();
                        st.task = Task::Error(format!("Read error during download: {}", e));
                        return;
                    }
                }
            }

            // Verify size
            if total_read as u64 != manifest.size {
                let mut st = s.lock().unwrap();
                st.task = Task::Error(format!(
                    "Size mismatch: expected {} bytes, got {} bytes",
                    manifest.size, total_read
                ));
                return;
            }

            // Verify hash
            let got = hex::encode(hasher.finalize());
            if got != manifest.sha256.to_lowercase() {
                let mut st = s.lock().unwrap();
                st.task = Task::Error(format!(
                    "Checksum mismatch: expected {}, got {}",
                    manifest.sha256, got
                ));
                return;
            }

            // Ask user for destination folder
            let dest_folder = match rfd::FileDialog::new()
                .set_title("Choose destination folder to save verified file")
                .pick_folder()
            {
                Some(p) => p,
                None => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error("No destination selected".into());
                    return;
                }
            };

            // Determine filename
            let filename = parsed
                .path_segments()
                .and_then(|mut s| s.next_back())
                .filter(|s| !s.is_empty())
                .unwrap_or("payload.bin")
                .to_string();

            let out_path = dest_folder.join(filename);

            // If file exists, try to create unique name
            let final_path = if out_path.exists() {
                let mut i = 1u32;
                let stem = out_path.file_stem().unwrap().to_string_lossy().to_string();
                let ext = out_path.extension().map(|e| e.to_string_lossy().to_string());
                loop {
                    let candidate_name = if let Some(extension) = &ext {
                        format!("{} ({}).{}", stem, i, extension)
                    } else {
                        format!("{} ({})", stem, i)
                    };
                    let candidate = out_path.with_file_name(&candidate_name);
                    if !candidate.exists() {
                        break candidate;
                    }
                    i += 1;
                }
            } else {
                out_path
            };

            // Save file
            {
                let mut st = s.lock().unwrap();
                st.task = Task::SavingFile;
            }
            match fs::File::create(&final_path) {
                Ok(mut f) => {
                    if let Err(e) = f.write_all(&buffer) {
                        let mut st = s.lock().unwrap();
                        st.task = Task::Error(format!("Failed to write file: {}", e));
                        return;
                    }
                    // On unix, add executable bit for convenience
                    #[cfg(unix)]
                    {
                        use std::os::unix::fs::PermissionsExt;
                        if let Ok(mut perms) = f.metadata().map(|m| m.permissions()) {
                            let mode = perms.mode();
                            perms.set_mode(mode | 0o755);
                            let _ = fs::set_permissions(&final_path, perms);
                        }
                    }
                }
                Err(e) => {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Could not create file: {}", e));
                    return;
                }
            }

            // Launch if checkbox was checked
            if auto_launch {
                {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Launching;
                }
                if let Err(e) = open::that(&final_path) {
                    let mut st = s.lock().unwrap();
                    st.task = Task::Error(format!("Failed to launch payload: {}", e));
                    return;
                }
            }

            let mut st = s.lock().unwrap();
            let msg = if auto_launch {
                format!("Saved and launched: {}", final_path.display())
            } else {
                format!("Saved: {}", final_path.display())
            };
            st.task = Task::Success(msg);
            
            // Reset fields after successful download
            st.manifest_path = None;
            st.loaded_manifest = None;
        });
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Handle manifest file passed via command line on first frame
        {
            let st = self.state.lock().unwrap();
            if let Some(path) = &st.manifest_path {
                if st.loaded_manifest.is_none() && !matches!(st.task, Task::LoadingManifest) {
                    let path_clone = path.clone();
                    drop(st);
                    self.load_manifest_background(path_clone);
                }
            }
        }

        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("Magnet");
                ui.separator();
                
                let mut st = self.state.lock().unwrap();
                let current = st.current_page.unwrap_or(Page::Create);
                
                if ui.selectable_label(current == Page::Create, "Create Manifest").clicked() {
                    st.current_page = Some(Page::Create);
                }
                if ui.selectable_label(current == Page::Install, "Install from Manifest").clicked() {
                    st.current_page = Some(Page::Install);
                }
            });
        });

        egui::CentralPanel::default().show(ctx, |ui| {
            let st = self.state.lock().unwrap();
            let current_page = st.current_page.unwrap_or(Page::Create);
            drop(st);

            match current_page {
                Page::Create => self.show_create_page(ui),
                Page::Install => self.show_install_page(ui),
            }

            ui.separator();
            
            // Show task/status
            let st = self.state.lock().unwrap();
            match &st.task {
                Task::Idle => {
                    ui.label("Status: Idle");
                }
                Task::ComputingHash => {
                    ui.label("Status: Computing SHA-256...");
                }
                Task::SavingManifest => {
                    ui.label("Status: Saving manifest...");
                }
                Task::LoadingManifest => {
                    ui.label("Status: Loading manifest...");
                }
                Task::Downloading => {
                    ui.label("Status: Downloading file...");
                }
                Task::Verifying => {
                    ui.label("Status: Verifying checksum & size...");
                }
                Task::SavingFile => {
                    ui.label("Status: Saving verified file...");
                }
                Task::Launching => {
                    ui.label("Status: Launching file...");
                }
                Task::Error(e) => {
                    ui.colored_label(egui::Color32::RED, format!("Error: {}", e));
                }
                Task::Success(msg) => {
                    ui.colored_label(egui::Color32::GREEN, format!("Success: {}", msg));
                }
            }
        });

        ctx.request_repaint_after(std::time::Duration::from_millis(200));
    }
}

impl App {
    fn show_create_page(&self, ui: &mut egui::Ui) {
        ui.heading("Create Magnet Manifest");
        ui.add_space(10.0);

        let app_clone = self.clone();
        let mut st = self.state.lock().unwrap();

        if ui.button("Select payload file").clicked() {
            drop(st);
            if let Some(p) = rfd::FileDialog::new().set_title("Select payload").pick_file() {
                app_clone.compute_hash_background(p);
            }
            st = self.state.lock().unwrap();
        }

        ui.add_space(5.0);

        if let Some(p) = &st.chosen_file {
            ui.label(format!("File: {}", p.display()));
        } else {
            ui.label("No file selected");
        }

        ui.add_space(10.0);

        let mut publisher = st.publisher.clone();
        let mut url = st.url.clone();

        ui.horizontal(|ui| {
            ui.label("Publisher:");
            ui.text_edit_singleline(&mut publisher);
        });

        ui.horizontal(|ui| {
            ui.label("HTTPS URL:");
            ui.text_edit_singleline(&mut url);
        });

        st.publisher = publisher;
        st.url = url;

        ui.add_space(10.0);
        ui.label(format!("SHA256: {}", st.computed_sha256));
        ui.label(format!("Size: {} bytes", st.computed_size));

        ui.add_space(10.0);

        let can_save = !st.computed_sha256.is_empty() && !st.publisher.is_empty() && st.url.starts_with("https://");
        if ui.add_enabled(can_save, egui::Button::new("Save .mgn")).clicked() {
            drop(st);
            if let Some(save_path) = rfd::FileDialog::new()
                .add_filter("Magnet manifest", &["mgn"])
                .set_file_name("manifest.mgn")
                .save_file()
            {
                app_clone.save_manifest_background(save_path);
            } else {
                let mut st = self.state.lock().unwrap();
                st.task = Task::Error("No save location selected".into());
            }
        }
    }

    fn show_install_page(&self, ui: &mut egui::Ui) {
        ui.heading("Install from Magnet Manifest");
        ui.add_space(10.0);

        let app_clone = self.clone();
        let mut st = self.state.lock().unwrap();

        if ui.button("Open .mgn file").clicked() {
            drop(st);
            if let Some(p) = rfd::FileDialog::new().add_filter("Magnet manifest", &["mgn"]).pick_file() {
                app_clone.load_manifest_background(p);
            }
            st = self.state.lock().unwrap();
        }

        ui.add_space(5.0);

        if let Some(p) = &st.manifest_path {
            ui.label(format!("Manifest: {}", p.display()));
        } else {
            ui.label("No manifest loaded");
        }

        ui.add_space(10.0);

        if let Some(m) = st.loaded_manifest.clone() {
            ui.group(|ui| {
                ui.label(format!("Publisher: {}", m.publisher));
                ui.label(format!("URL: {}", m.url));
                ui.label(format!("SHA256: {}", m.sha256));
                ui.label(format!("Size: {} bytes", m.size));
            });

            ui.add_space(10.0);
            ui.checkbox(&mut st.auto_launch, "Automatically launch after download");
            ui.add_space(10.0);

            if ui.button("Trust & Download").clicked() {
                let msg = format!("Publisher: {}\nDownload size: {} bytes\n\nDo you trust this source?", m.publisher, m.size);
                let auto_launch = st.auto_launch;
                drop(st);
                let user_ok = rfd::MessageDialog::new()
                    .set_description(&msg)
                    .set_buttons(rfd::MessageButtons::YesNo)
                    .show();
                if user_ok == rfd::MessageDialogResult::Yes {
                    app_clone.download_and_verify_background(auto_launch);
                } else {
                    let mut st = self.state.lock().unwrap();
                    st.task = Task::Idle;
                }
            }
        }
    }
}

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([800.0, 500.0])
            .with_title("Magnet")
            .with_decorations(true)
            .with_resizable(true),
        ..Default::default()
    };
    eframe::run_native(
        "Magnet",
        options,
        Box::new(|cc| Ok(Box::new(App::new(cc)))),
    )
}