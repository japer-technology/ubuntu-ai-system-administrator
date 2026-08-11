 Here is the full catalog of commands currently available in the Hermes registry, categorized by their primary function:                               
                                                                                                                                                          
    📋 Session Management                                                                                                                                 
                                                                                                                                                          
    • /start — Acknowledge platform start pings.                                                                                                          
    • /new — Start a new session (fresh session ID + history) [name]                                                                                      
    • /topic — Enable/inspect Telegram DM topic sessions [off|help|session-id]                                                                            
    • /clear — Clear screen and start a new session.                                                                                                      
    • /redraw — Force a full UI repaint.                                                                                                                  
    • /history — Show conversation history.                                                                                                               
    • /save — Save the current conversation.                                                                                                              
    • /retry — Retry the last message.                                                                                                                    
    • /undo — Back up N user turns and re-prompt [N]                                                                                                      
    • /title — Set a title for the current session [name]                                                                                                 
    • /handoff — Hand off this session to a platform (Telegram, Discord, etc.) <platform>                                                                 
    • /branch — Branch the current session (explore a different path) [name]                                                                              
    • /compress — Compress conversation context [here [N] | focus topic]                                                                                  
    • /rollback — List or restore filesystem checkpoints [number]                                                                                         
    • /snapshot — Create/restore state snapshots [create|restore <id>|prune]                                                                              
    • /stop — Kill all running background processes.                                                                                                      
    • /approve — Approve a pending dangerous command [session|always]                                                                                     
    • /deny — Deny a pending dangerous command.                                                                                                           
    • /background — Run a prompt in the background <prompt>                                                                                               
    • /agents — Show active agents and running tasks.                                                                                                     
    • /queue — Queue a prompt for the next turn <prompt>                                                                                                  
    • /steer — Inject a message after the next tool call <prompt>                                                                                         
    • /goal — Set a standing goal Hermes works on [text | pause | resume | clear | status]                                                                
    • /subgoal — Add/manage extra criteria on the active goal [text | remove N | clear]                                                                   
    • /status — Show session info.                                                                                                                        
    • /sethome — Set this chat as the home channel.                                                                                                       
    • /resume — Resume a previously-named session [name]                                                                                                  
    • /sessions — Browse and resume previous sessions.                                                                                                    
    • /restart — Gracefully restart the gateway.                                                                                                          
                                                                                                                                                          
    ⚙️  Configuration & Personalization                                                                                                                    
                                                                                                                                                          
    • /config — Show current configuration.                                                                                                               
    • /model — Switch model for this session [model] [--provider name] [--global] [--refresh]                                                             
    • /codex-runtime — Toggle codex app-server runtime [auto|codex_app_server]                                                                            
    • /gquota — Show Google Gemini Code Assist quota usage.                                                                                               
    • /personality — Set a predefined personality [name]                                                                                                  
    • /statusbar — Toggle the context/model status bar.                                                                                                   
    • /verbose — Cycle tool progress display: off -> new -> all -> verbose                                                                                
    • /footer — Toggle gateway runtime-metadata footer [on|off|status]                                                                                    
    • /yolo — Toggle YOLO mode (skip all dangerous command approvals).                                                                                    
    • /reasoning — Manage reasoning effort and display [level|show|hide]                                                                                  
    • /fast — Toggle fast mode (Priority Processing) [normal|fast|status]                                                                                 
    • /skin — Show or change the display skin/theme [name]                                                                                                
    • /indicator — Pick the TUI busy-indicator style [kaomoji|emoji|unicode|ascii]                                                                        
    • /voice — Toggle voice mode [on|off|tts|status]                                                                                                      
    • /busy — Control what Enter does while Hermes is working [queue|steer|interrupt|status]                                                              
                                                                                                                                                          
    🛠️  Tools & Skills                                                                                                                                     
                                                                                                                                                          
    • /tools — Manage tools [list|disable|enable] [name...]                                                                                               
    • /toolsets — List available toolsets.                                                                                                                
    • /skills — Search, install, inspect, or manage skills.                                                                                               
    • /memory — Review pending memory writes [pending|approve|reject|approval] [id|on|off]                                                                
    • /bundles — List skill bundles.                                                                                                                      
    • /cron — Manage scheduled tasks [subcommand]                                                                                                         
    • /curator — Background skill maintenance [status|run|pause|resume|pin|unpin|restore|list-archived]                                                   
    • /kanban — Multi-profile collaboration board [subcommand]                                                                                            
    • /reload — Reload .env variables into the running session.                                                                                           
    • /reload-mcp — Reload MCP servers from config.                                                                                                       
    • /reload-skills — Re-scan ~/.hermes/skills/ for changes.                                                                                             
    • /browser — Connect browser tools via CDP [connect|disconnect|status]                                                                                
    • /plugins — List installed plugins and their status.                                                                                                 
                                                                                                                                                          
    ℹ️  Info & Utilities                                                                                                                                   
                                                                                                                                                          
    • /commands — Browse all commands and skills (paginated) [page]                                                                                       
    • /help — Show available commands.                                                                                                                    
    • /usage — Show token usage and rate limits.                                                                                                          
    • /insights — Show usage insights and analytics [days]                                                                                                
    • /platforms — Show gateway/messaging platform status.                                                                                                
    • /platform — Pause, resume, or list a failing gateway platform <pause|resume|list> [name]                                                            
    • /copy — Copy the last assistant response to clipboard [number]                                                                                      
    • /paste — Attach clipboard image from your clipboard.                                                                                                
    • /image — Attach a local image file <path>                                                                                                           
    • /update — Update Hermes Agent to the latest version.                                                                                                
    • /version — Show Hermes Agent version.                                                                                                               
    • /debug — Upload debug report and get shareable links.                                                                                               
    • /whoami — Show your slash command access (admin / user).                                                                                            
    • /profile — Show active profile name and home directory.                                                                                             
                                                                                                                                                          
    🚪 Exit                                                                                                                                               
                                                                                                                                                          
    • /quit — Exit the CLI (can also --delete session history) [--delete]                                                                                 

    Beyond the slash-command registry above, Hermes Chat leans on a set
    of interactive command-line affordances — history recall, line
    editing, input prefixes, and variable expansion — that make the chat
    box feel like a real shell. They are catalogued here for the same
    "what could our chat UI borrow" reason as the commands.

    ⌨️  Keyboard & Line Editing

    • ↑ / ↓ — Walk backwards/forwards through your input history; recall a
      previous prompt to re-run or edit it without retyping.
    • ↑ after typing a prefix — Prefix-filtered recall: only step through
      earlier inputs that start with what you have already typed.
    • Ctrl-R — Reverse-incremental search across the whole input history.
    • Tab — Autocomplete slash commands, sub-commands, skill names, file
      paths, and @mentions.
    • Shift+Enter / Alt+Enter — Insert a newline for multi-line prompts
      instead of sending.
    • Enter — Send (its behaviour while Hermes is working is governed by
      /busy: queue, steer, or interrupt).
    • Ctrl-C — Interrupt the current turn and cancel running tool calls
      (see /stop).
    • Ctrl-L — Clear the screen and repaint (see /clear, /redraw).
    • Ctrl-A / Ctrl-E, Alt-←/→, Ctrl-W, Ctrl-U / Ctrl-K — Emacs-style line
      editing: jump to start/end, move by word, delete word/line.
    • Esc — Dismiss the autocomplete/command palette or cancel the
      in-progress edit.
    • PageUp / PageDown — Scroll the transcript without disturbing your
      draft input.

    🔣 Input Shortcuts & Prefixes

    • / — Open the slash-command palette; keep typing to fuzzy-filter the
      catalog above.
    • @ — Mention or attach a workspace file/path into the prompt (with
      path autocompletion).
    • ! — Run the rest of the line as a one-off shell command (still
      subject to the approval gate).
    • # — Drop a quick memory/note for Hermes to remember (see /memory).
    • Drag-and-drop / paste — Attach an image or file inline (see /image,
      /paste).
    • Markdown — Compose prompts and read replies with Markdown and
      fenced code blocks.

    🧩 Variables & Templating

    • $VAR / ${VAR} — Expand environment variables from the session's
      .env inside a prompt; refresh them live with /reload.
    • Command & skill arguments — Pass positional and --named arguments to
      slash commands and skills (e.g. /model gpt-5 --provider openai
      --global).
    • Custom commands / aliases — Save a frequently used prompt or command
      chain under a short name and re-invoke it.
    • Standing goals & subgoals — /goal and /subgoal behave like
      persistent variables Hermes keeps working against across turns.

    🧰 Other Command-Line Usefulness

    • Persistent, named sessions — History survives restarts; resume,
      branch, or browse it (/resume, /branch, /sessions).
    • Queue / steer while busy — Line up the next prompt or inject
      mid-tool guidance without waiting (/queue, /steer, /busy).
    • Copy output — Yank the last assistant reply to the clipboard
      (/copy).
    • Status bar & footer — Live model/context/runtime readout you can
      toggle (/statusbar, /footer).
    • Verbose & reasoning toggles — Control how much tool and reasoning
      detail is shown inline (/verbose, /reasoning).
    • Themes & indicators — Re-skin the TUI and pick a busy-indicator
      style (/skin, /indicator).
