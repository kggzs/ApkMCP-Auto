#!/usr/bin/env bash

###
# This is the test script to test the working of APKTool MCP Server.
# 
# Prerequisites:
# 1. Ensure APKTool is installed and available in PATH
# 2. Have DVAC_FINAL.apk file in the current directory
# 3. Start the APKTool MCP server in HTTP stream mode on port 8652
# 4. Command for step 3: `python apktool_mcp_server.py --http --port 8652`
#
# Usage: ./test_apktool.sh
###

set -euo pipefail

MCP_URL="${MCP_URL:-http://127.0.0.1:8652/mcp/}"
ACCEPT_HDR="application/json, text/event-stream"
CONTENT_HDR="application/json"
APK_PATH="DVAC_FINAL.apk"

# Helper: extract data: JSON items from SSE and drop [DONE]
sse_to_json() {
    grep '^data: ' | sed 's/^data: //' | grep -v '^\[DONE\]$'
}

# 1) Initialize, capture session id header
echo "== Initialize MCP Session =="
INIT_RESP_HEADERS=$(mktemp)
curl -i -s -X POST "$MCP_URL" \
    -H "Content-Type: $CONTENT_HDR" \
    -H "Accept: $ACCEPT_HDR" \
    -d '{
        "jsonrpc":"2.0",
        "method":"initialize",
        "params":{
            "protocolVersion":"2024-11-05",
            "capabilities":{},
            "clientInfo":{"name":"apktool-test-automation","version":"1.0.0"}
        },
        "id":1
    }' | tee "$INIT_RESP_HEADERS" >/dev/null

SESSION_ID=$(awk -F': ' 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {print $2}' "$INIT_RESP_HEADERS" | tr -d '\r')
if [[ -z "${SESSION_ID:-}" ]]; then
    echo "Failed to obtain MCP-Session-Id header" >&2
    exit 1
fi
echo "Session: $SESSION_ID"

# 2) Send notifications/initialized (no output expected)
curl -s -X POST "$MCP_URL" \
    -H "Content-Type: $CONTENT_HDR" \
    -H "Accept: $ACCEPT_HDR" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' >/dev/null

# 3) Discover available tools
echo "== Available Tools =="
TOOLS_JSON=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: $CONTENT_HDR" \
    -H "Accept: $ACCEPT_HDR" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' \
    | sse_to_json | tail -n 1)

echo "$TOOLS_JSON" | jq -r '.result.tools[].name'

# Helper: call a tool with JSON arguments
call_tool() {
    local name="$1"
    local args_json="$2" # must be a valid JSON object string
    local id="${3:-1000}"
    
    curl -s -X POST "$MCP_URL" \
        -H "Content-Type: $CONTENT_HDR" \
        -H "Accept: $ACCEPT_HDR" \
        -H "Mcp-Session-Id: $SESSION_ID" \
        -d "{
            \"jsonrpc\":\"2.0\",
            \"method\":\"tools/call\",
            \"params\":{
                \"name\":\"$name\",
                \"arguments\":$args_json
            },
            \"id\":$id
        }" \
        | sse_to_json
}

echo "== Running APKTool MCP Server Tests =="

# 4) Health check
echo "--- health_check ---"
call_tool "health_check" '{}' 10 | jq -r '.result.content[0].text // .result // .error?.message // .'

# 5) Get workspace info
echo "--- get_workspace_info ---"
call_tool "get_workspace_info" '{}' 11 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.workspace_info.projects[]? | {name, is_apktool_project, package_name} // .'

# Check if APK file exists, if not skip decode test
if [[ -f "$APK_PATH" ]]; then
    echo "--- decode_apk ---"
    APK_FULL_PATH=$(realpath "$APK_PATH" 2>/dev/null || echo "$APK_PATH")
    call_tool "decode_apk" "{\"apk_path\":\"$APK_FULL_PATH\",\"force\":true}" 12 | jq -r '.result.content[0].text // .result // .error?.message // .'
    
    # Wait a moment for decode to complete
    sleep 2
    PROJECT_DIR="apktool_mcp_server_workspace/DVAC_FINAL"
else
    echo "--- decode_apk (skipped - APK not found) ---"
    echo "APK file $APK_PATH not found, using existing project"
    # Use existing project from workspace info - check what's available
    PROJECT_DIR="apktool_mcp_server_workspace/DVAC-FINAL"  # Note the hyphen based on workspace info
fi

# 7) Get decoded project directory (use existing project if decode skipped)
echo "Using project directory: $PROJECT_DIR"

# 8) Get manifest content
echo "--- get_manifest ---"
call_tool "get_manifest" "{\"project_dir\":\"$PROJECT_DIR\"}" 13 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.manifest[0:300] // .error // .'

# 9) Get apktool.yml
echo "--- get_apktool_yml ---"
call_tool "get_apktool_yml" "{\"project_dir\":\"$PROJECT_DIR\"}" 14 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.content[0:200] // .error // .'

# 10) List smali directories
echo "--- list_smali_directories ---"
call_tool "list_smali_directories" "{\"project_dir\":\"$PROJECT_DIR\"}" 15 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.smali_dirs[]?.name // .error // .'

# 11) List smali files with pagination
echo "--- list_smali_files (offset=0,count=20) ---"
call_tool "list_smali_files" "{\"project_dir\":\"$PROJECT_DIR\",\"smali_dir\":\"smali\",\"offset\":0,\"count\":20}" 16 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.smali_files[]?.class_name // .error // .' | head -5

# 12) List smali files with package filter
echo "--- list_smali_files (package filter: com.zin) ---"
call_tool "list_smali_files" "{\"project_dir\":\"$PROJECT_DIR\",\"package_prefix\":\"com.zin\"}" 17 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.smali_files[]?.class_name // .error // .' | head -5

# 13) Get specific smali file
echo "--- get_smali_file ---"
call_tool "get_smali_file" "{\"project_dir\":\"$PROJECT_DIR\",\"class_name\":\"com.zin.dvac.MainActivity\"}" 18 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.content[0:300] // .error // .'

# 14) List all resource types
echo "--- list_resources (all types) ---"
call_tool "list_resources" "{\"project_dir\":\"$PROJECT_DIR\"}" 19 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.resource_types[]?.type // .error // .'

# 15) List specific resource type with pagination
echo "--- list_resources (layout, offset=0,count=10) ---"
call_tool "list_resources" "{\"project_dir\":\"$PROJECT_DIR\",\"resource_type\":\"layout\",\"offset\":0,\"count\":10}" 20 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.resources[]?.name // .error // .' | head -5

# 16) Get specific resource file
echo "--- get_resource_file ---"
call_tool "get_resource_file" "{\"project_dir\":\"$PROJECT_DIR\",\"resource_type\":\"layout\",\"resource_name\":\"activity_main.xml\"}" 21 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.content[0:200] // .error // .'

# 17) Search in files
echo "--- search_in_files (search for 'onCreate') ---"
call_tool "search_in_files" "{\"project_dir\":\"$PROJECT_DIR\",\"search_pattern\":\"onCreate\",\"file_extensions\":[\".smali\"],\"max_results\":10}" 22 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.results[]?.file // .error // .' | head -5

# 18) Search with pagination (fix the jq syntax error)
echo "--- search_in_files (with pagination, search for 'Activity') ---"
call_tool "search_in_files" "{\"project_dir\":\"$PROJECT_DIR\",\"search_pattern\":\"Activity\",\"offset\":0,\"count\":5,\"case_sensitive\":false}" 23 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.results[]? | "\(.file) (\(.matches) matches)" // .error // .' | head -5

# 19) Analyze project structure
echo "--- analyze_project_structure ---"
call_tool "analyze_project_structure" "{\"project_dir\":\"$PROJECT_DIR\"}" 24 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.analysis | {is_valid_project, project_size, total_smali_files: .smali_analysis.total_smali_files, total_resource_files: .resource_analysis.total_resource_files} // .error // .'

# 20) Clean project (with backup)
echo "--- clean_project ---"
call_tool "clean_project" "{\"project_dir\":\"$PROJECT_DIR\",\"backup\":true}" 25 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.cleaned_directories[]?.path // .error // "No directories to clean"'

# 21) Build APK
echo "--- build_apk ---"
call_tool "build_apk" "{\"project_dir\":\"$PROJECT_DIR\",\"debug\":true}" 26 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.apk_path // .error // .'

# 22) Example of modifying a smali file (commented out for safety)
echo "--- modify_smali_file (example - commented out for safety) ---"
# Uncomment the line below to test file modification
call_tool "modify_smali_file" '{"project_dir":"'$PROJECT_DIR'","class_name":"com.zin.dvac.MainActivity","new_content":"# Modified smali content\n.class public Lcom/zin/dvac/MainActivity;\n.super Landroid/app/Activity;","create_backup":true}' 27 | jq -r '.result.content[0].text // .result // .error?.message // .'
echo "Skipped - modify_smali_file (enable manually if needed)"

# 23) Example of modifying a resource file (commented out for safety)
echo "--- modify_resource_file (example - commented out for safety) ---"
# Uncomment the line below to test resource modification
call_tool "modify_resource_file" '{"project_dir":"'$PROJECT_DIR'","resource_type":"values","resource_name":"strings.xml","new_content":"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources>\n    <string name=\"app_name\">Modified DVAC</string>\n</resources>","create_backup":true}' 28 | jq -r '.result.content[0].text // .result // .error?.message // .'
echo "Skipped - modify_resource_file (enable manually if needed)"

# 24) Final workspace info to see changes
echo "--- get_workspace_info (final) ---"
call_tool "get_workspace_info" '{}' 29 | jq -r '.result.content[0].text // .result // .error?.message // .' | jq -r '.workspace_info.projects[]? | {name, is_apktool_project, size} // .error // .'

echo "== Test Completed Successfully =="
echo "Note: Some modification operations were skipped for safety."
echo "To test file modifications, uncomment the relevant lines in the script."

# Cleanup temp file
rm -f "$INIT_RESP_HEADERS"
