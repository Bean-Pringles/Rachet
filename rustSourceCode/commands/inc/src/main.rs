use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Usage: {} <variable_name> [amount]", args[0]);
        std::process::exit(1);
    }
    
    let variable_name = &args[1];
    let amount = if args.len() > 2 {
        match args[2].parse::<i32>() {
            Ok(amt) => amt,
            Err(_) => {
                eprintln!("Error: Amount '{}' is not a valid integer", args[2]);
                std::process::exit(1);
            }
        }
    } else {
        1 // Default amount
    };
    
    // Output Rust-style increment statement
    println!("{} += {};", variable_name, amount);
}