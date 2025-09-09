use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::{self, Read};
use std::path::Path;
use std::process::{Command, Stdio};

#[derive(Serialize, Deserialize, Debug)]
struct RachetToken {
    command: String,
    args: Vec<String>,
    line: i32,
}

#[derive(Debug)]
struct CommandExecutor {
    commands_dir: String,
    available_commands: HashMap<String, String>,
}

impl CommandExecutor {
    fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let commands_dir = "compiler/commands";
        let mut executor = CommandExecutor {
            commands_dir: commands_dir.to_string(),
            available_commands: HashMap::new(),
        };
        
        executor.discover_commands()?;
        Ok(executor)
    }
    
    fn discover_commands(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let commands_path = Path::new(&self.commands_dir);
        
        if !commands_path.exists() {
            return Err(format!("Commands directory '{}' not found", self.commands_dir).into());
        }
        
        if !commands_path.is_dir() {
            return Err(format!("'{}' is not a directory", self.commands_dir).into());
        }
        
        for entry in fs::read_dir(commands_path)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_file() {
                if let Some(file_name) = path.file_name() {
                    if let Some(file_str) = file_name.to_str() {
                        // Look for .exe files on Windows or any executable on Unix
                        let is_executable = if cfg!(windows) {
                            file_str.ends_with(".exe")
                        } else {
                            // On Unix, check if file is executable
                            #[cfg(unix)]
                            {
                                use std::os::unix::fs::PermissionsExt;
                                if let Ok(metadata) = entry.metadata() {
                                    metadata.permissions().mode() & 0o111 != 0
                                } else {
                                    false
                                }
                            }
                            #[cfg(not(unix))]
                            true
                        };
                        
                        if is_executable {
                            let command_name = if cfg!(windows) {
                                file_str.strip_suffix(".exe").unwrap_or(file_str)
                            } else {
                                file_str
                            };
                            
                            self.available_commands.insert(
                                command_name.to_string(),
                                path.to_string_lossy().to_string(),
                            );
                        }
                    }
                }
            }
        }
        
        if self.available_commands.is_empty() {
            eprintln!("Warning: No executable commands found in '{}'", self.commands_dir);
        } else {
            eprintln!("Discovered commands: {:?}", self.available_commands.keys().collect::<Vec<_>>());
        }
        
        Ok(())
    }
    
    fn execute_token(&self, token: &RachetToken) -> Result<(), Box<dyn std::error::Error>> {
        match token.command.as_str() {
            "print" => self.handle_print(&token.args, token.line),
            cmd => self.execute_external_command(cmd, &token.args, token.line),
        }
    }
    
    fn handle_print(&self, args: &[String], line: i32) -> Result<(), Box<dyn std::error::Error>> {
        if args.is_empty() {
            eprintln!("Error on line {}: print command requires an argument", line);
            return Err("print command requires an argument".into());
        }
        
        println!("{}", args[0]);
        Ok(())
    }
    
    fn execute_external_command(
        &self,
        command_name: &str,
        args: &[String],
        line: i32,
    ) -> Result<(), Box<dyn std::error::Error>> {
        match self.available_commands.get(command_name) {
            Some(command_path) => {
                let mut cmd = Command::new(command_path);
                cmd.args(args);
                cmd.stdout(Stdio::piped());
                cmd.stderr(Stdio::piped());
                
                match cmd.output() {
                    Ok(output) => {
                        // Print stdout from the command
                        if !output.stdout.is_empty() {
                            print!("{}", String::from_utf8_lossy(&output.stdout));
                        }
                        
                        // Print stderr to stderr
                        if !output.stderr.is_empty() {
                            eprint!("{}", String::from_utf8_lossy(&output.stderr));
                        }
                        
                        if !output.status.success() {
                            eprintln!(
                                "Error on line {}: Command '{}' failed with exit code {:?}",
                                line, command_name, output.status.code()
                            );
                            return Err(format!("Command '{}' failed", command_name).into());
                        }
                        
                        Ok(())
                    }
                    Err(e) => {
                        eprintln!("Error on line {}: Failed to execute '{}': {}", line, command_name, e);
                        Err(e.into())
                    }
                }
            }
            None => {
                eprintln!("Error on line {}: Unknown command '{}'", line, command_name);
                eprintln!("Available commands: {:?}", self.available_commands.keys().collect::<Vec<_>>());
                Err(format!("Unknown command '{}'", command_name).into())
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Read JSON from stdin instead of command line arguments
    let mut stdin = io::stdin();
    let mut json_input = String::new();
    stdin.read_to_string(&mut json_input)?;
    
    if json_input.trim().is_empty() {
        eprintln!("Error: No JSON input provided via stdin");
        std::process::exit(1);
    }
    
    // Parse JSON tokens
    let tokens: Vec<RachetToken> = match serde_json::from_str(&json_input) {
        Ok(tokens) => tokens,
        Err(e) => {
            eprintln!("Error parsing JSON input: {}", e);
            eprintln!("Input was: {}", json_input);
            std::process::exit(1);
        }
    };
    
    // Create command executor
    let executor = match CommandExecutor::new() {
        Ok(exec) => exec,
        Err(e) => {
            eprintln!("Error initializing command executor: {}", e);
            std::process::exit(1);
        }
    };
    
    // Execute tokens
    for token in &tokens {
        if let Err(e) = executor.execute_token(token) {
            eprintln!("Execution failed: {}", e);
            std::process::exit(1);
        }
    }
    
    Ok(())
}