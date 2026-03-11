
# playwright-cli

## Description

CLI for common Playwright actions. Record and generate Playwright code, inspect selectors and take screenshots.

## README

### playwright-cli
Playwright CLI with SKILLS

### Playwright CLI vs Playwright MCP
This package provides CLI interface into Playwright. If you are using **coding agents**, that is the best fit.

*   **CLI**: Modern **coding agents** increasingly favor CLI–based workflows exposed as SKILLS over MCP because CLI invocations are more token-efficient: they avoid loading large tool schemas and verbose accessibility trees into the model context, allowing agents to act through concise, purpose-built commands. This makes CLI + SKILLs better suited for high-throughput coding agents that must balance browser automation with large codebases, tests, and reasoning within limited context windows.
*   **MCP**: MCP remains relevant for specialized agentic loops that benefit from persistent state, rich introspection, and iterative reasoning over page structure, such as exploratory automation, self-healing tests, or long-running autonomous workflows where maintaining continuous browser context outweighs token cost concerns. Learn more about [Playwright MCP](https://github.com/microsoft/playwright-mcp).

### Key Features
*   **Token-efficient**. Does not force page data into LLM.

### Requirements
*   Node.js 18 or newer
*   Claude Code, GitHub Copilot, or any other coding agent.

## Getting Started

## Installation
```
npm install -g @playwright/cli@latest
```

### Installing skills
Claude Code, GitHub Copilot and others will use the locally installed skills.
```
playwright-cli install --skills
```

### Skills-less operation
Point your agent at the CLI and let it cook. It'll read the skill off `playwright-cli --help` on its own:
```
Test the "add todo" flow on https://demo.playwright.dev/todomvc using playwright-cli. Check playwright-cli --help for available commands.
```

## Demo
```
> Use playwright skills to test https://demo.playwright.dev/todomvc/. Take screenshots for all successful and failing scenarios.
```
Your agent will be running commands, but it does not mean you can't play with it manually:
```
playwright-cli open https://demo.playwright.dev/todomvc/ --headed
playwright-cli type "Buy groceries"
playwright-cli press Enter
playwright-cli type "Water flowers"
playwright-cli press Enter
playwright-cli check e21
playwright-cli check e35
playwright-cli screenshot
```

## Headed operation
Playwright CLI is headless by default. If you'd like to see the browser, pass `"--headed"` to `open`:
```
playwright-cli open https://playwright.dev --headed
```

## Sessions
Playwright CLI keeps the browser profile in memory by default. Your cookies and storage state are preserved between CLI calls within the session, but lost when the browser closes. Use `"--persistent"` to save the profile to disk for persistence across browser restarts.

You can use different instances of the browser for different projects with sessions. Pass `-s=` to the invocation to talk to a specific browser.
```
playwright-cli open https://playwright.dev
playwright-cli -s=example open https://example.com --persistent
playwright-cli list
```
You can run your coding agent with the `PLAYWRIGHT_CLI_SESSION` environment variable:
```
PLAYWRIGHT_CLI_SESSION=todo-app claude .
```
Or instruct it to prepend `-s=` to the calls.

Manage your sessions as follows:
```
playwright-cli list # list all sessions
playwright-cli close-all # close all browsers
playwright-cli kill-all # forcefully kill all browser processes
```

## Monitoring
Use `playwright-cli show` to open a visual dashboard that lets you see and control all running browser sessions. This is useful when your coding agents are running browser automation in the background and you want to observe their progress or step in to help.
```
playwright-cli show
```
The dashboard opens a window with two views:
*   **Session grid** — shows all active sessions grouped by workspace, each with a live screencast preview, session name, current URL, and page title. Click any session to zoom in.
*   **Session detail** — shows a live view of the selected session with a tab bar, navigation controls (back, forward, reload, address bar), and full remote control. Click into the viewport to take over mouse and keyboard input; press Escape to release.

From the grid you can also close running sessions or delete data for inactive ones.

## Commands

### Core
```
playwright-cli open [url] # open browser, optionally navigate to url
playwright-cli goto <url> # navigate to a url
playwright-cli close # close the page
playwright-cli type <text> # type text into editable element
playwright-cli click <ref> [button] # perform click on a web page
playwright-cli dblclick <ref> [button] # perform double click on a web page
playwright-cli fill <ref> <text> # fill text into editable element
playwright-cli drag <startRef> <endRef> # perform drag and drop between two elements
playwright-cli hover <ref> # hover over element on page
playwright-cli select <ref> <val> # select an option in a dropdown
playwright-cli upload <file> # upload one or multiple files
playwright-cli check <ref> # check a checkbox or radio button
playwright-cli uncheck <ref> # uncheck a checkbox or radio button
playwright-cli snapshot # capture page snapshot to obtain element ref
playwright-cli snapshot --filename=f # save snapshot to specific file
playwright-cli eval <func> [ref] # evaluate javascript expression on page or element
playwright-cli dialog-accept [prompt] # accept a dialog
playwright-cli dialog-dismiss # dismiss a dialog
playwright-cli resize <w> <h> # resize the browser window
```

### Navigation
```
playwright-cli go-back # go back to the previous page
playwright-cli go-forward # go forward to the next page
playwright-cli reload # reload the current page
```

### Keyboard
```
playwright-cli press <key> # press a key on the keyboard, `a`, `arrowleft`
playwright-cli keydown <key> # press a key down on the keyboard
playwright-cli keyup <key> # press a key up on the keyboard
```

### Mouse
```
playwright-cli mousemove <x> <y> # move mouse to a given position
playwright-cli mousedown [button] # press mouse down
playwright-cli mouseup [button] # press mouse up
playwright-cli mousewheel <dx> <dy> # scroll mouse wheel
```

### Save as
```
playwright-cli screenshot [ref] # screenshot of the current page or element
playwright-cli screenshot --filename=f # save screenshot with specific filename
playwright-cli pdf # save page as pdf
playwright-cli pdf --filename=page.pdf # save pdf with specific filename
```

### Tabs
```
playwright-cli tab-list # list all tabs
playwright-cli tab-new [url] # create a new tab
playwright-cli tab-close [index] # close a browser tab
playwright-cli tab-select <index> # select a browser tab
```

### Storage
```
playwright-cli state-save [filename] # save storage state
playwright-cli state-load <filename> # load storage state
# Cookies
playwright-cli cookie-list [--domain] # list cookies
playwright-cli cookie-get <name> # get a cookie
playwright-cli cookie-set <name> <val> # set a cookie
playwright-cli cookie-delete <name> # delete a cookie
playwright-cli cookie-clear # clear all cookies
# LocalStorage
playwright-cli localstorage-list # list localStorage entries
playwright-cli localstorage-get <key> # get localStorage value
playwright-cli localstorage-set <k> <v> # set localStorage value
playwright-cli localstorage-delete <k> # delete localStorage entry
playwright-cli localstorage-clear # clear all localStorage
# SessionStorage
playwright-cli sessionstorage-list # list sessionStorage entries
playwright-cli sessionstorage-get <k> # get sessionStorage value
playwright-cli sessionstorage-set <k> <v> # set sessionStorage value
playwright-cli sessionstorage-delete <k> # delete sessionStorage entry
playwright-cli sessionstorage-clear # clear all sessionStorage
```

### Network
```
playwright-cli route <pattern> [opts] # mock network requests
playwright-cli route-list # list active routes
playwright-cli unroute [pattern] # remove route(s)
```

### DevTools
```
playwright-cli console [min-level] # list console messages
playwright-cli network # list all network requests since loading the page
playwright-cli run-code <code> # run playwright code snippet
playwright-cli tracing-start # start trace recording
playwright-cli tracing-stop # stop trace recording
playwright-cli video-start # start video recording
playwright-cli video-stop [filename] # stop video recording
```

### Open parameters
```
playwright-cli open --browser=chrome # use specific browser
playwright-cli open --extension # connect via browser extension
playwright-cli open --persistent # use persistent profile
playwright-cli open --profile=<path> # use custom profile directory
playwright-cli open --config=file.json # use config file
playwright-cli close # close the browser
playwright-cli delete-data # delete user data for default session
```

### Snapshots
After each command, playwright-cli provides a snapshot of the current browser state.
```
> playwright-cli goto https://example.com
### Page
- Page URL: https://example.com/
- Page Title: Example Domain
### Snapshot
[Snapshot](.playwright-cli/page-2026-02-14T19-22-42-679Z.yml)
```
You can also take a snapshot on demand using `playwright-cli snapshot` command.

If `"--filename"` is not provided, a new snapshot file is created with a timestamp. Default to automatic file naming, use `"--filename="` when artifact is a part of the workflow result.

### Sessions
```
playwright-cli -s=name <cmd> # run command in named session
playwright-cli -s=name close # stop a named browser
playwright-cli -s=name delete-data # delete user data for named browser
playwright-cli list # list all sessions
playwright-cli close-all # close all browsers
playwright-cli kill-all # forcefully kill all browser processes
```

### Local installation
In some cases you might want to install playwright-cli locally. If running the globally available `playwright-cli` binary fails, use `npx playwright-cli` to run the commands. For example:
```
npx playwright-cli open https://example.com
npx playwright-cli click e1
```

## Configuration file
The Playwright CLI can be configured using a JSON configuration file. You can specify the configuration file using the `"--config"` command line option:
```
playwright-cli --config path/to/config.json open example.com
```
Playwright CLI will load config from `.playwright/cli.config.json` by default so that you did not need to specify it every time.

## Specific tasks
The installed skill includes detailed reference guides for common tasks:
*   **Request mocking** — intercept and mock network requests
*   **Running Playwright code** — execute arbitrary Playwright scripts
*   **Browser session management** — manage multiple browser sessions
*   **Storage state (cookies, localStorage)** — persist and restore browser state
*   **Test generation** — generate Playwright tests from interactions
*   **Tracing** — record and inspect execution traces
*   **Video recording** — capture browser session videos
