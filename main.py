import os
import json
from groq import Groq
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client with API key from environment
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
# Initialize Rich console for formatted output
console = Console()


# 1. Load config

def load_config(path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    with open(path) as f:
        return json.load(f)


# 2. Single completion

def complete(
    user_message: str,
    system_prompt: str,
    config: dict,
    few_shot: list = None
) -> tuple[str, dict]:
    """
    Run one completion and return (reply_text, usage_dict).
    few_shot is a list of {"user": ..., "assistant": ...} dicts.
    """
    # Start with system prompt
    messages = [{"role": "system", "content": system_prompt}]

    # Inject few-shot examples before the actual user message
    if few_shot:
        for example in few_shot:
            messages.append({"role": "user",    "content": example["user"]})
            messages.append({"role": "assistant", "content": example["assistant"]})

    # Add the current user message
    messages.append({"role": "user", "content": user_message})

    # Call Groq API with configured parameters
    response = client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    # Extract response text and usage statistics
    reply = response.choices[0].message.content
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
    }
    return reply, usage


# 3. Display helpers

def show_ab_comparison(prompt_a: str, prompt_b: str, reply_a: str, reply_b: str):
    """Print two responses side by side in panels."""
    # Create panel for first prompt/response
    panel_a = Panel(
        reply_a,
        title="[bold green]Prompt A[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    # Create panel for second prompt/response
    panel_b = Panel(
        reply_b,
        title="[bold blue]Prompt B[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    # Display both panels side by side
    console.print(Columns([panel_a, panel_b]))


def show_temperature_sweep(message: str, config: dict):
    """Run same prompt at temps 0.0, 0.5, 1.0 and show all three."""
    console.print("\n[bold]Temperature sweep — same prompt, three temperatures[/bold]\n")

    # Test three different temperature values
    for temp in [0.0, 0.5, 1.0]:
        # Create modified config with current temperature
        tweaked = {**config, "temperature": temp}
        reply, usage = complete(message, config["system_prompt_a"], tweaked)

        # Display result with temperature label
        console.print(Panel(
            reply,
            title=f"[bold yellow]temperature = {temp}[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        ))
        # Show token usage
        console.print(
            f"  [dim]tokens: {usage['total_tokens']}[/dim]\n"
        )


# 4. Modes

def mode_ab_test(config: dict):
    """Compare system_prompt_a vs system_prompt_b on every message."""
    console.print("\n[bold cyan]Mode: A/B prompt comparison[/bold cyan]")
    # Show preview of both prompts
    console.print(f"[dim]Prompt A:[/dim] {config['system_prompt_a'][:80]}...")
    console.print(f"[dim]Prompt B:[/dim] {config['system_prompt_b'][:80]}...\n")

    # Interactive loop for comparing prompts
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        # Get responses from both prompts
        reply_a, usage_a = complete(user_input, config["system_prompt_a"], config)
        reply_b, usage_b = complete(user_input, config["system_prompt_b"], config)

        # Display side-by-side comparison
        show_ab_comparison(
            config["system_prompt_a"], config["system_prompt_b"],
            reply_a, reply_b
        )
        # Show token usage for both
        console.print(
            f"[dim]tokens — A: {usage_a['total_tokens']} | "
            f"B: {usage_b['total_tokens']}[/dim]\n"
        )

def mode_few_shot(config: dict):
    """Chat using few-shot examples from config."""
    examples = config.get("few_shot_examples", [])
    console.print(f"\n[bold cyan]Mode: Few-shot prompting[/bold cyan]")
    console.print(f"[dim]Loaded {len(examples)} examples from config.json[/dim]\n")

    # Display all few-shot examples
    for ex in examples:
        console.print(f"  [dim]example → user:[/dim] {ex['user']}")
        console.print(f"  [dim]          asst:[/dim] {ex['assistant']}\n")

    console.print("[dim]Now ask your own questions — the model follows the pattern above.[/dim]\n")

    # Interactive loop using few-shot examples
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        # Complete with few-shot examples included
        reply, usage = complete(
            user_input,
            config["system_prompt_a"],
            config,
            few_shot=examples
        )

        # Display response
        console.print(Panel(reply, border_style="magenta", box=box.ROUNDED))
        console.print(f"[dim]tokens: {usage['total_tokens']}[/dim]\n")


def mode_temperature_sweep(config: dict):
    """Run one message at multiple temperatures."""
    # Get user input for temperature testing
    user_input = input("Enter a message to sweep: ").strip()
    if user_input:
        show_temperature_sweep(user_input, config)

def mode_free_chat(config: dict):
    """Standard chat using system_prompt_a."""
    console.print(f"\n[bold cyan]Mode: Free chat[/bold cyan]")
    console.print(f"[dim]System:[/dim] {config['system_prompt_a']}\n")

    # Maintain conversation history
    history = []

    # Interactive chat loop
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() == "quit":
            break

        # Add user message to history
        history.append({"role": "user", "content": user_input})

        # Generate response with full conversation context
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": config["system_prompt_a"]},
                *history
            ],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )

        # Extract and store assistant response
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

        # Display response and metadata
        console.print(Panel(reply, border_style="green", box=box.ROUNDED))
        console.print(
            f"[dim]tokens: {response.usage.total_tokens} | "
            f"temp: {config['temperature']}[/dim]\n"
        )

def main():
    """Main entry point - load config and present mode selection menu."""
    # Load configuration from JSON
    config = load_config()

    # Display configuration details
    console.print(Panel(
        "[bold]Prompt Engineering Playground[/bold]\n"
        f"Model: {config['model']} | "
        f"Temp: {config['temperature']} | "
        f"Max tokens: {config['max_tokens']}",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    # Show available modes
    console.print("\nSelect a mode:\n")
    console.print("  [green]1[/green] — Free chat (single system prompt)")
    console.print("  [green]2[/green] — A/B prompt comparison")
    console.print("  [green]3[/green] — Few-shot prompting")
    console.print("  [green]4[/green] — Temperature sweep\n")

    # Get user's mode selection
    choice = input("Mode (1-4): ").strip()

    # Route to selected mode
    if   choice == "1": mode_free_chat(config)
    elif choice == "2": mode_ab_test(config)
    elif choice == "3": mode_few_shot(config)
    elif choice == "4": mode_temperature_sweep(config)
    else: console.print("[red]Invalid choice.[/red]")

if __name__ == "__main__":
    main()