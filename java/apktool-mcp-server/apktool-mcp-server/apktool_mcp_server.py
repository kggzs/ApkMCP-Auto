# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "logging", "argparse" ]
# ///

"""
Copyright (c) 2025 apktool mcp server developer(s) (https://github.com/zinja-coder/apktool-mcp-server)
See the file 'LICENSE' for copying permission
"""

import logging
import subprocess
import os
import shutil
import argparse
import json
import time
import xml.etree.ElementTree as ET
from typing import List, Union, Dict, Optional, Callable, Any
from fastmcp import FastMCP

# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Parse arguments
parser = argparse.ArgumentParser("APKTool MCP Server")
parser.add_argument("--http", help="Serve MCP Server over HTTP stream.", action="store_true", default=False)
parser.add_argument("--port", help="Specify the port number for --http to serve on. (default:8652)", default=8652, type=int)
parser.add_argument("--workspace", help="Specify workspace directory for APK projects", default="apktool_mcp_server_workspace", type=str)
parser.add_argument("--timeout", help="Default timeout for APKTool commands in seconds", default=300, type=int)
parser.add_argument("--apktool-path", help="Full path to apktool executable (bat or jar)", default=None, type=str)
args = parser.parse_args()

# Initialize the MCP server
mcp = FastMCP("APKTool-MCP Server with Advanced Features")

# Current workspace for decoded APK projects
WORKSPACE_DIR = os.environ.get("APKTOOL_WORKSPACE", args.workspace)
DEFAULT_TIMEOUT = args.timeout

# APKTool executable path
APKTOOL_EXECUTABLE = args.apktool_path if args.apktool_path else "apktool"

# Ensure workspace directory exists
os.makedirs(WORKSPACE_DIR, exist_ok=True)

class PaginationUtils:
    """Utility class for handling pagination across different MCP tools"""
    
    # Configuration constants
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 10000
    MAX_OFFSET = 1000000
    
    @staticmethod
    def validate_pagination_params(offset: int, count: int) -> tuple[int, int]:
        """Validate and normalize pagination parameters"""
        offset = max(0, min(offset, PaginationUtils.MAX_OFFSET))
        count = max(0, min(count, PaginationUtils.MAX_PAGE_SIZE))
        return offset, count
    
    @staticmethod
    def handle_pagination(
        items: List[Any],
        offset: int = 0,
        count: int = 0,
        data_type: str = "paginated-list",
        items_key: str = "items",
        item_transformer: Optional[Callable[[Any], Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic pagination handler for list data
        
        Args:
            items: List of items to paginate
            offset: Starting offset
            count: Number of items to return (0 means use default)
            data_type: Type identifier for the response
            items_key: Key name for items in response
            item_transformer: Optional function to transform items
            
        Returns:
            Paginated response dictionary
        """
        if items is None:
            items = []
            
        total_items = len(items)
        
        # Validate parameters
        offset, count = PaginationUtils.validate_pagination_params(offset, count)
        
        # Determine effective limit
        if count == 0:
            effective_limit = min(PaginationUtils.DEFAULT_PAGE_SIZE, max(0, total_items - offset))
        else:
            effective_limit = min(count, max(0, total_items - offset))
        
        # Calculate bounds
        start_index = min(offset, total_items)
        end_index = min(start_index + effective_limit, total_items)
        has_more = end_index < total_items
        
        # Extract and transform paginated subset
        paginated_items = items[start_index:end_index]
        if item_transformer:
            paginated_items = [item_transformer(item) for item in paginated_items]
        
        # Build response
        result = {
            "type": data_type,
            items_key: paginated_items,
            "pagination": {
                "total": total_items,
                "offset": offset,
                "limit": effective_limit,
                "count": len(paginated_items),
                "has_more": has_more
            }
        }
        
        # Add navigation helpers
        if has_more:
            result["pagination"]["next_offset"] = end_index
            
        if offset > 0:
            prev_offset = max(0, offset - effective_limit)
            result["pagination"]["prev_offset"] = prev_offset
            
        # Page calculations
        if effective_limit > 0:
            current_page = (offset // effective_limit) + 1
            total_pages = (total_items + effective_limit - 1) // effective_limit
            result["pagination"]["current_page"] = current_page
            result["pagination"]["total_pages"] = total_pages
            result["pagination"]["page_size"] = effective_limit
            
        return result

class ValidationUtils:
    """Utility class for input validation"""
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = True) -> Dict[str, Union[bool, str]]:
        """Validate file/directory path"""
        if not path or not isinstance(path, str):
            return {"valid": False, "error": "Path cannot be empty"}
            
        if must_exist and not os.path.exists(path):
            return {"valid": False, "error": f"Path does not exist: {path}"}
            
        return {"valid": True}
    
    @staticmethod
    def validate_class_name(class_name: str) -> Dict[str, Union[bool, str]]:
        """Validate Java class name format"""
        if not class_name or not isinstance(class_name, str):
            return {"valid": False, "error": "Class name cannot be empty"}
            
        if not class_name.replace('.', '').replace('_', '').replace('$', '').replace('/', '').isalnum():
            return {"valid": False, "error": "Invalid class name format"}
            
        return {"valid": True}
     
    @staticmethod
    def validate_search_pattern(pattern: str) -> Dict[str, Union[bool, str]]:
        """Validate search pattern"""
        if not pattern or not isinstance(pattern, str):
            return {"valid": False, "error": "Search pattern cannot be empty"}
            
        if len(pattern) > 1000:
            return {"valid": False, "error": "Search pattern too long (max 1000 characters)"}
            
        return {"valid": True}

# Enhanced command runner with better error handling
def run_command(command: List[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[str] = None) -> Dict[str, Union[str, int, bool]]:
    """Enhanced command runner with comprehensive error handling"""
    try:
        logger.info(f"Running command: {' '.join(command)}")
        
        # Input validation
        if not command or not all(isinstance(arg, str) for arg in command):
            return {
                "success": False,
                "error": "Invalid command format"
            }
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout,
            cwd=cwd
        )
        
        logger.info(f"Command completed successfully with return code {result.returncode}")
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": " ".join(command)
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}: {e.stderr}")
        return {
            "success": False,
            "stdout": e.stdout or "",
            "stderr": e.stderr or "",
            "returncode": e.returncode,
            "error": f"Command failed with return code {e.returncode}",
            "command": " ".join(command)
        }
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds")
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "command": " ".join(command)
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "error": "APKTool not found. Please ensure APKTool is installed and in PATH"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error running command: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "command": " ".join(command)
        }

# Health check functionality
@mcp.tool()
async def health_check() -> Dict:
    """
    Check the health status of the APKTool MCP server and APKTool installation.
    
    Returns:
        Dictionary containing server status and APKTool availability
    """
    try:
        # Check APKTool installation
        apktool_result = run_command([APKTOOL_EXECUTABLE, "--version"], timeout=10)
        
        result = {
            "server_status": "running",
            "workspace_dir": WORKSPACE_DIR,
            "workspace_exists": os.path.exists(WORKSPACE_DIR),
            "apktool_available": apktool_result["success"],
            "timestamp": time.time()
        }
        
        if apktool_result["success"]:
            result["apktool_version"] = apktool_result["stdout"].strip()
        else:
            result["apktool_error"] = apktool_result["error"]
            
        logger.info("APKTool MCP Server: Health check completed")
        return result
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "server_status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

# Enhanced MCP Tools with validation and better error handling

@mcp.tool()
async def decode_apk(
    apk_path: str,
    force: bool = True,
    no_res: bool = False,
    no_src: bool = False,
    output_dir: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict:
    """
    Decode an APK file using APKTool with comprehensive validation and error handling.
    
    Args:
        apk_path: Path to the APK file to decode
        force: Force delete destination directory if it exists
        no_res: Do not decode resources
        no_src: Do not decode sources
        output_dir: Custom output directory (optional)
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary with operation results including validation details
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(apk_path, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    if not apk_path.lower().endswith(('.apk', '.xapk')):
        return {"success": False, "error": "File must have .apk or .xapk extension"}
    
    # Determine output directory
    if output_dir is None:
        apk_name = os.path.basename(apk_path).rsplit('.', 1)[0]
        output_dir = os.path.join(WORKSPACE_DIR, apk_name)
    
    # Build command
    command = [APKTOOL_EXECUTABLE, "d", apk_path, "-o", output_dir]
    if force:
        command.append("-f")
    if no_res:
        command.append("-r")
    if no_src:
        command.append("-s")
    
    result = run_command(command, timeout=timeout)
    
    if result["success"]:
        # Additional validation - check if output directory was created
        if os.path.exists(output_dir):
            result["output_dir"] = output_dir
            result["workspace"] = WORKSPACE_DIR
            
            # Get basic project info
            manifest_path = os.path.join(output_dir, "AndroidManifest.xml")
            apktool_yml_path = os.path.join(output_dir, "apktool.yml")
            
            result["has_manifest"] = os.path.exists(manifest_path)
            result["has_apktool_yml"] = os.path.exists(apktool_yml_path)
        else:
            result["warning"] = "Decode reported success but output directory not found"
    
    return result

@mcp.tool()
async def build_apk(
    project_dir: str,
    output_apk: Optional[str] = None,
    debug: bool = True,
    force_all: bool = False,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict:
    """
    Build an APK file from a decoded APKTool project with enhanced validation.
    
    Args:
        project_dir: Path to the APKTool project directory
        output_apk: Optional output APK path
        debug: Build with debugging info
        force_all: Force rebuild all files
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary with operation results and build information
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    if not os.path.isdir(project_dir):
        return {"success": False, "error": f"Project path is not a directory: {project_dir}"}
    
    # Check for required files
    apktool_yml = os.path.join(project_dir, "apktool.yml")
    manifest_xml = os.path.join(project_dir, "AndroidManifest.xml")
    
    if not os.path.exists(apktool_yml):
        return {"success": False, "error": "apktool.yml not found. Is this a valid APKTool project?"}
    
    if not os.path.exists(manifest_xml):
        return {"success": False, "error": "AndroidManifest.xml not found. Is this a valid APKTool project?"}
    
    # Build command
    command = ["apktool", "b", project_dir]
    if debug:
        command.append("-d")
    if force_all:
        command.append("-f")
    if output_apk:
        command.extend(["-o", output_apk])
    
    result = run_command(command, timeout=timeout)
    
    if result["success"]:
        # Determine built APK path
        if not output_apk:
            output_apk = os.path.join(project_dir, "dist", os.path.basename(project_dir) + ".apk")
        
        if os.path.exists(output_apk):
            result["apk_path"] = output_apk
            result["apk_size"] = os.path.getsize(output_apk)
        else:
            result["warning"] = f"Build succeeded but APK not found at expected path: {output_apk}"
    
    return result

@mcp.tool()
async def get_manifest(project_dir: str) -> Dict:
    """
    Get the AndroidManifest.xml content from a decoded APK project with validation.
    
    Args:
        project_dir: Path to the APKTool project directory
        
    Returns:
        Dictionary with manifest content, metadata, and validation results
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    manifest_path = os.path.join(project_dir, "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        return {
            "success": False,
            "error": f"AndroidManifest.xml not found in {project_dir}",
            "expected_path": manifest_path
        }
    
    try:
        with open(manifest_path, 'r', encoding="utf-8") as f:
            content = f.read()
 
        result = {
            "success": True,
            "manifest": content,
            "path": manifest_path,
            "size": os.path.getsize(manifest_path),
            "encoding": "utf-8"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error reading manifest: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to read AndroidManifest.xml: {str(e)}",
            "path": manifest_path
        }

@mcp.tool()
async def get_apktool_yml(project_dir: str) -> Dict:
    """
    Get apktool.yml information from a decoded APK project with validation.
    
    Args:
        project_dir: Path to APKTool project directory
        
    Returns:
        Dictionary with apktool.yml content, metadata, and validation results
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    yml_path = os.path.join(project_dir, "apktool.yml")
    if not os.path.exists(yml_path):
        return {
            "success": False,
            "error": f"apktool.yml not found in {project_dir}",
            "expected_path": yml_path
        }
    
    try:
        with open(yml_path, 'r', encoding="utf-8") as f:
            content = f.read()
                    
        result = {
            "success": True,
            "content": content,
            "path": yml_path,
            "size": os.path.getsize(yml_path),
            "encoding": "utf-8"
        }
         
        return result
        
    except Exception as e:
        logger.error(f"Error reading apktool.yml: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to read apktool.yml: {str(e)}",
            "path": yml_path
        }

@mcp.tool()
async def list_smali_directories(project_dir: str) -> Dict:
    """
    List all smali directories in a project with enhanced metadata.
    
    Args:
        project_dir: Path to the APKTool project directory
        
    Returns:
        Dictionary with list of smali directories and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    try:
        smali_dirs = []
        for d in os.listdir(project_dir):
            dir_path = os.path.join(project_dir, d)
            if d.startswith("smali") and os.path.isdir(dir_path):
                # Count files in smali directory
                file_count = 0
                try:
                    for root, _, files in os.walk(dir_path):
                        file_count += len([f for f in files if f.endswith('.smali')])
                except Exception as e:
                    logger.warning(f"Error counting files in {dir_path}: {e}")
                    file_count = 0
                
                smali_dirs.append({
                    "name": d,
                    "path": dir_path,
                    "smali_file_count": file_count
                })
        
        return {
            "success": True,
            "smali_dirs": smali_dirs,
            "count": len(smali_dirs)
        }
        
    except Exception as e:
        logger.error(f"Error listing smali directories: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list smali directories: {str(e)}"
        }

@mcp.tool()
async def list_smali_files(
    project_dir: str,
    smali_dir: str = "smali",
    package_prefix: Optional[str] = None,
    offset: int = 0,
    count: int = 0
) -> Dict:
    """
    List smali files with pagination support and enhanced filtering.
    
    Args:
        project_dir: Path to the APKTool project directory
        smali_dir: Which smali directory to use (smali, smali_classes2, etc.)
        package_prefix: Optional package prefix to filter by (e.g., "com.example")
        offset: Starting offset for pagination
        count: Number of items to return (0 means use default)
        
    Returns:
        Paginated dictionary with list of smali files and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    smali_path = os.path.join(project_dir, smali_dir)
    if not os.path.exists(smali_path):
        # Get available smali directories
        try:
            smali_dirs = [d for d in os.listdir(project_dir)
                         if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        except Exception:
            smali_dirs = []
        
        return {
            "success": False,
            "error": f"Smali directory not found: {smali_path}",
            "available_dirs": smali_dirs
        }
    
    try:
        smali_files = []
        search_root = smali_path
        
        # Handle package filtering
        if package_prefix:
            # Validate package name format
            if not package_prefix.replace('.', '').replace('_', '').replace('$', '').isalnum():
                return {"success": False, "error": "Invalid package prefix format"}
            
            package_path = os.path.join(smali_path, package_prefix.replace('.', os.path.sep))
            if not os.path.exists(package_path):
                return {
                    "success": False,
                    "error": f"Package not found: {package_prefix}",
                    "expected_path": package_path
                }
            search_root = package_path
        
        # Recursively find all .smali files
        for root, _, files in os.walk(search_root):
            for file in files:
                if file.endswith(".smali"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, smali_path)
                    class_name = rel_path.replace(os.path.sep, '.').replace('.smali', '')
                    
                    smali_files.append({
                        "class_name": class_name,
                        "file_path": file_path,
                        "rel_path": rel_path,
                        "size": os.path.getsize(file_path)
                    })
        
        # Sort by class name for consistent results
        smali_files.sort(key=lambda x: x["class_name"])
        
        # Apply pagination
        paginated_result = PaginationUtils.handle_pagination(
            items=smali_files,
            offset=offset,
            count=count,
            data_type="smali-files",
            items_key="smali_files"
        )
        
        # Add metadata
        paginated_result["success"] = True
        paginated_result["smali_dir"] = smali_dir
        paginated_result["package_prefix"] = package_prefix
        paginated_result["search_root"] = search_root
        
        return paginated_result
        
    except Exception as e:
        logger.error(f"Error listing smali files: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list smali files: {str(e)}"
        }

@mcp.tool()
async def get_smali_file(project_dir: str, class_name: str) -> Dict:
    """
    Get content of a specific smali file by class name with validation.
    
    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)
        
    Returns:
        Dictionary with smali file content and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    class_validation = ValidationUtils.validate_class_name(class_name)
    if not class_validation["valid"]:
        return {"success": False, "error": class_validation["error"]}
    
    try:
        # Look for the class in all smali directories
        smali_dirs = [d for d in os.listdir(project_dir)
                     if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        
        for smali_dir in smali_dirs:
            file_path = os.path.join(
                project_dir,
                smali_dir,
                class_name.replace('.', os.path.sep) + '.smali'
            )
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding="utf-8") as f:
                    content = f.read()
                
                return {
                    "success": True,
                    "content": content,
                    "file_path": file_path,
                    "smali_dir": smali_dir,
                    "size": os.path.getsize(file_path),
                    "class_name": class_name,
                    "encoding": "utf-8"
                }
        
        return {
            "success": False,
            "error": f"Smali file not found for class: {class_name}",
            "searched_dirs": smali_dirs
        }
        
    except Exception as e:
        logger.error(f"Error getting smali file: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get smali file: {str(e)}"
        }

@mcp.tool()
async def modify_smali_file(
    project_dir: str,
    class_name: str,
    new_content: str,
    create_backup: bool = True
) -> Dict:
    """
    Modify smali file content with validation and backup support.
    
    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)
        new_content: New content for the smali file
        create_backup: Whether to create a backup of the original file
        
    Returns:
        Dictionary with operation results and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    class_validation = ValidationUtils.validate_class_name(class_name)
    if not class_validation["valid"]:
        return {"success": False, "error": class_validation["error"]}
     
    try:
        # Find the smali file
        smali_dirs = [d for d in os.listdir(project_dir)
                     if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        
        file_path = None
        for smali_dir in smali_dirs:
            test_path = os.path.join(
                project_dir,
                smali_dir,
                class_name.replace('.', os.path.sep) + '.smali'
            )
            
            if os.path.exists(test_path):
                file_path = test_path
                break
        
        if not file_path:
            return {
                "success": False,
                "error": f"Smali file not found for class: {class_name}",
                "searched_dirs": smali_dirs
            }
        
        # Get original content size
        original_size = os.path.getsize(file_path)
        
        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = f"{file_path}.bak.{int(time.time())}"
            shutil.copy2(file_path, backup_path)
        
        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"Successfully modified {file_path}",
            "file_path": file_path,
            "backup_path": backup_path,
            "class_name": class_name,
            "original_size": original_size,
            "new_size": len(new_content),
            "backup_created": backup_path is not None
        }
        
    except Exception as e:
        logger.error(f"Error modifying smali file: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to modify smali file: {str(e)}"
        }

@mcp.tool()
async def list_resources(
    project_dir: str,
    resource_type: Optional[str] = None,
    offset: int = 0,
    count: int = 0
) -> Dict:
    """
    List resources with pagination support and enhanced metadata.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Optional resource type to filter by (e.g., "layout", "drawable")
        offset: Starting offset for pagination
        count: Number of items to return (0 means use default)
        
    Returns:
        Paginated dictionary with list of resources and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    res_path = os.path.join(project_dir, "res")
    if not os.path.exists(res_path):
        return {
            "success": False,
            "error": f"Resources directory not found: {res_path}"
        }
    
    try:
        if resource_type:
            # List resources of specific type
            type_path = os.path.join(res_path, resource_type)
            if not os.path.exists(type_path):
                # Get available resource types
                resource_types = [
                    d for d in os.listdir(res_path)
                    if os.path.isdir(os.path.join(res_path, d))
                ]
                
                return {
                    "success": False,
                    "error": f"Resource type directory not found: {resource_type}",
                    "available_types": resource_types
                }
            
            resources = []
            for item in os.listdir(type_path):
                item_path = os.path.join(type_path, item)
                if os.path.isfile(item_path):
                    resources.append({
                        "name": item,
                        "path": item_path,
                        "size": os.path.getsize(item_path),
                        "type": resource_type,
                        "extension": os.path.splitext(item)[1],
                        "modified_time": os.path.getmtime(item_path)
                    })
            
            # Sort by name
            resources.sort(key=lambda x: x["name"])
            
            # Apply pagination
            paginated_result = PaginationUtils.handle_pagination(
                items=resources,
                offset=offset,
                count=count,
                data_type="resources",
                items_key="resources"
            )
            
            paginated_result["success"] = True
            paginated_result["resource_type"] = resource_type
            paginated_result["resource_path"] = type_path
            
            return paginated_result
        
        else:
            # List all resource types with counts
            resource_types = []
            for item in os.listdir(res_path):
                type_path = os.path.join(res_path, item)
                if os.path.isdir(type_path):
                    try:
                        files = [f for f in os.listdir(type_path) if os.path.isfile(os.path.join(type_path, f))]
                        resource_count = len(files)
                        
                        # Calculate total size
                        total_size = 0
                        for f in files:
                            try:
                                total_size += os.path.getsize(os.path.join(type_path, f))
                            except:
                                pass
                        
                        resource_types.append({
                            "type": item,
                            "path": type_path,
                            "count": resource_count,
                            "total_size": total_size
                        })
                    except Exception as e:
                        logger.warning(f"Error processing resource type {item}: {e}")
                        resource_types.append({
                            "type": item,
                            "path": type_path,
                            "count": 0,
                            "total_size": 0,
                            "error": str(e)
                        })
            
            # Sort by type name
            resource_types.sort(key=lambda x: x["type"])
            
            # Apply pagination
            paginated_result = PaginationUtils.handle_pagination(
                items=resource_types,
                offset=offset,
                count=count,
                data_type="resource-types",
                items_key="resource_types"
            )
            
            paginated_result["success"] = True
            
            return paginated_result
        
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list resources: {str(e)}"
        }

@mcp.tool()
async def get_resource_file(project_dir: str, resource_type: str, resource_name: str) -> Dict:
    """
    Get content of a specific resource file with validation and metadata.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Resource type (e.g., "layout", "drawable")
        resource_name: Name of the resource file
        
    Returns:
        Dictionary with resource file content and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    if not resource_type or not resource_name:
        return {"success": False, "error": "Resource type and name are required"}
    
    resource_path = os.path.join(project_dir, "res", resource_type, resource_name)
    if not os.path.exists(resource_path):
        return {
            "success": False,
            "error": f"Resource file not found: {resource_path}",
            "expected_path": resource_path
        }
    
    try:
        file_size = os.path.getsize(resource_path)
        is_text_file = True
        
        # Try to read as text first
        try:
            with open(resource_path, 'r', encoding="utf-8") as f:
                content = f.read()
            encoding = "utf-8"
        except UnicodeDecodeError:
            is_text_file = False
            content = None
            encoding = None
        
        
        if is_text_file and content is not None:    
            result = {
                "success": True,
                "content": content,
                "path": resource_path,
                "size": file_size,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "encoding": encoding
            }
            
            return result
        else:
            # Binary file
            return {
                "success": False,
                "error": "This appears to be a binary resource file and cannot be read as text",
                "path": resource_path,
                "size": file_size,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "is_binary": True,
                "is_text": False
            }
        
    except Exception as e:
        logger.error(f"Error getting resource file: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get resource file: {str(e)}"
        }

@mcp.tool()
async def modify_resource_file(
    project_dir: str,
    resource_type: str,
    resource_name: str,
    new_content: str,
    create_backup: bool = True
) -> Dict:
    """
    Modify the content of a specific resource file with validation and backup support.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Resource type (e.g., "layout", "values")
        resource_name: Name of the resource file
        new_content: New content for the resource file
        create_backup: Whether to create a backup of the original file
        
    Returns:
        Dictionary with operation results and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    if not resource_type or not resource_name:
        return {"success": False, "error": "Resource type and name are required"}
    
    resource_path = os.path.join(project_dir, "res", resource_type, resource_name)
    if not os.path.exists(resource_path):
        return {
            "success": False,
            "error": f"Resource file not found: {resource_path}",
            "expected_path": resource_path
        }
    
    try:
        # Get original file info
        original_size = os.path.getsize(resource_path)
        
        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = f"{resource_path}.bak.{int(time.time())}"
            shutil.copy2(resource_path, backup_path)
        
        # Write new content
        with open(resource_path, 'w', encoding="utf-8") as f:
            f.write(new_content)
        
        result = {
            "success": True,
            "message": f"Successfully modified {resource_path}",
            "path": resource_path,
            "backup_path": backup_path,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "original_size": original_size,
            "new_size": len(new_content),
            "backup_created": backup_path is not None
        }
         
        return result
        
    except Exception as e:
        logger.error(f"Error modifying resource file: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to modify resource file: {str(e)}"
        }

@mcp.tool()
async def search_in_files(
    project_dir: str,
    search_pattern: str,
    file_extensions: List[str] = [".smali", ".xml"],
    max_results: int = 100,
    offset: int = 0,
    count: int = 0,
    case_sensitive: bool = False
) -> Dict:
    """
    Search for patterns in files with pagination and enhanced filtering.
    
    Args:
        project_dir: Path to the APKTool project directory
        search_pattern: Text pattern to search for
        file_extensions: List of file extensions to search in
        max_results: Maximum total results to collect before pagination
        offset: Starting offset for pagination
        count: Number of items to return (0 means use default)
        case_sensitive: Whether search should be case sensitive
        
    Returns:
        Paginated dictionary with search results and metadata
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    pattern_validation = ValidationUtils.validate_search_pattern(search_pattern)
    if not pattern_validation["valid"]:
        return {"success": False, "error": pattern_validation["error"]}
    
    if not file_extensions or not isinstance(file_extensions, list):
        return {"success": False, "error": "File extensions must be a non-empty list"}
    
    try:
        results = []
        search_stats = {
            "files_searched": 0,
            "files_matched": 0,
            "total_matches": 0,
            "search_truncated": False,
            "directories_searched": 0,
            "start_time": time.time()
        }
        
        # Prepare search pattern
        pattern = search_pattern if case_sensitive else search_pattern.lower()
        
        # Walk through project directory
        for root, dirs, files in os.walk(project_dir):
            search_stats["directories_searched"] += 1
            
            for file in files:
                if len(results) >= max_results:
                    search_stats["search_truncated"] = True
                    break
                
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    search_stats["files_searched"] += 1
                    
                    try:
                        with open(file_path, 'r', encoding="utf-8") as f:
                            content = f.read()
                        
                        # Perform search
                        search_content = content if case_sensitive else content.lower()
                        if pattern in search_content:
                            search_stats["files_matched"] += 1
                            
                            # Count matches in this file and find line numbers
                            matches_in_file = search_content.count(pattern)
                            search_stats["total_matches"] += matches_in_file
                            
                            # Find line numbers of matches
                            lines = content.splitlines()
                            line_matches = []
                            for i, line in enumerate(lines, 1):
                                search_line = line if case_sensitive else line.lower()
                                if pattern in search_line:
                                    line_matches.append({
                                        "line_number": i,
                                        "line_content": line.strip()[:200],  # Truncate long lines
                                        "matches_in_line": search_line.count(pattern)
                                    })
                            
                            rel_path = os.path.relpath(file_path, project_dir)
                            results.append({
                                "file": rel_path,
                                "path": file_path,
                                "size": os.path.getsize(file_path),
                                "matches": matches_in_file,
                                "extension": os.path.splitext(file)[1],
                                "line_matches": line_matches[:10],  # Limit to first 10 line matches
                                "total_line_matches": len(line_matches)
                            })
                    
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue
                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {str(e)}")
                        continue
            
            if search_stats["search_truncated"]:
                break
        
        search_stats["end_time"] = time.time()
        search_stats["duration"] = search_stats["end_time"] - search_stats["start_time"]
        
        # Sort by number of matches (descending) then by file name
        results.sort(key=lambda x: (-x["matches"], x["file"]))
        
        # Apply pagination
        paginated_result = PaginationUtils.handle_pagination(
            items=results,
            offset=offset,
            count=count,
            data_type="search-results",
            items_key="results"
        )
        
        # Add search metadata
        paginated_result["success"] = True
        paginated_result["search_pattern"] = search_pattern
        paginated_result["case_sensitive"] = case_sensitive
        paginated_result["file_extensions"] = file_extensions
        paginated_result["search_stats"] = search_stats
        
        return paginated_result
        
    except Exception as e:
        logger.error(f"Error searching in files: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to search in files: {str(e)}"
        }

@mcp.tool()
async def clean_project(project_dir: str, backup: bool = True) -> Dict:
    """
    Clean a project directory to prepare for rebuilding with enhanced backup support.
    
    Args:
        project_dir: Path to the APKTool project directory
        backup: Whether to create a backup of build directories before cleaning
        
    Returns:
        Dictionary with operation results and cleanup details
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    try:
        dirs_to_clean = ["build", "dist", "temp"]
        files_to_clean = ["*.tmp", "*.log"]
        cleaned_dirs = []
        cleaned_files = []
        backed_up = []
        
        # Clean directories
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(project_dir, dir_name)
            if os.path.exists(dir_path):
                if backup:
                    # Create backup
                    backup_path = f"{dir_path}_backup_{int(time.time())}"
                    shutil.copytree(dir_path, backup_path)
                    backed_up.append({
                        "original": dir_path,
                        "backup": backup_path,
                        "type": "directory"
                    })
                
                # Calculate size before removal
                dir_size = 0
                file_count = 0
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            dir_size += os.path.getsize(file_path)
                            file_count += 1
                        except:
                            pass
                
                # Remove directory
                shutil.rmtree(dir_path)
                cleaned_dirs.append({
                    "path": dir_path,
                    "size_freed": dir_size,
                    "files_removed": file_count
                })
        
        # Clean specific files
        import glob
        for pattern in files_to_clean:
            pattern_path = os.path.join(project_dir, pattern)
            for file_path in glob.glob(pattern_path):
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    
                    if backup:
                        backup_path = f"{file_path}.bak.{int(time.time())}"
                        shutil.copy2(file_path, backup_path)
                        backed_up.append({
                            "original": file_path,
                            "backup": backup_path,
                            "type": "file"
                        })
                    
                    os.remove(file_path)
                    cleaned_files.append({
                        "path": file_path,
                        "size": file_size
                    })
        
        total_size_freed = sum(d["size_freed"] for d in cleaned_dirs) + sum(f["size"] for f in cleaned_files)
        total_files_removed = sum(d["files_removed"] for d in cleaned_dirs) + len(cleaned_files)
        
        return {
            "success": True,
            "cleaned_directories": cleaned_dirs,
            "cleaned_files": cleaned_files,
            "backed_up_items": backed_up,
            "total_size_freed": total_size_freed,
            "total_files_removed": total_files_removed,
            "backup_created": len(backed_up) > 0
        }
        
    except Exception as e:
        logger.error(f"Error cleaning project: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to clean project: {str(e)}"
        }

@mcp.tool()
async def analyze_project_structure(project_dir: str) -> Dict:
    """
    Analyze the structure of a decoded APK project and provide comprehensive metadata.
    
    Args:
        project_dir: Path to the APKTool project directory
        
    Returns:
        Dictionary with detailed project analysis
    """
    # Input validation
    path_validation = ValidationUtils.validate_path(project_dir, must_exist=True)
    if not path_validation["valid"]:
        return {"success": False, "error": path_validation["error"]}
    
    try:
        analysis = {
            "project_path": project_dir,
            "analysis_time": time.time(),
            "is_valid_project": False,
            "project_size": 0,
            "file_counts": {},
            "directory_structure": {},
            "smali_analysis": {},
            "resource_analysis": {},
            "manifest_analysis": {},
            "errors": []
        }
        
        # Check if it's a valid APKTool project
        required_files = ["AndroidManifest.xml", "apktool.yml"]
        missing_files = []
        
        for file in required_files:
            if not os.path.exists(os.path.join(project_dir, file)):
                missing_files.append(file)
        
        analysis["is_valid_project"] = len(missing_files) == 0
        if missing_files:
            analysis["errors"].append(f"Missing required files: {', '.join(missing_files)}")
        
        # Calculate total project size and file counts
        total_size = 0
        file_counts = {}
        
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    total_size += size
                    
                    ext = os.path.splitext(file)[1].lower()
                    if not ext:
                        ext = "(no extension)"
                    
                    if ext not in file_counts:
                        file_counts[ext] = {"count": 0, "size": 0}
                    
                    file_counts[ext]["count"] += 1
                    file_counts[ext]["size"] += size
                    
                except Exception as e:
                    analysis["errors"].append(f"Error processing file {file_path}: {str(e)}")
        
        analysis["project_size"] = total_size
        analysis["file_counts"] = file_counts
        
        # Directory structure analysis
        directories = {}
        for item in os.listdir(project_dir):
            item_path = os.path.join(project_dir, item)
            if os.path.isdir(item_path):
                try:
                    # Count files in directory
                    file_count = 0
                    dir_size = 0
                    
                    for root, _, files in os.walk(item_path):
                        file_count += len(files)
                        for file in files:
                            try:
                                dir_size += os.path.getsize(os.path.join(root, file))
                            except:
                                pass
                    
                    directories[item] = {
                        "path": item_path,
                        "file_count": file_count,
                        "size": dir_size
                    }
                except Exception as e:
                    analysis["errors"].append(f"Error analyzing directory {item}: {str(e)}")
        
        analysis["directory_structure"] = directories
        
        # Smali analysis
        smali_dirs = [d for d in directories.keys() if d.startswith("smali")]
        smali_analysis = {
            "smali_directories": smali_dirs,
            "total_smali_files": 0,
            "package_distribution": {}
        }
        
        for smali_dir in smali_dirs:
            smali_path = os.path.join(project_dir, smali_dir)
            for root, _, files in os.walk(smali_path):
                smali_files = [f for f in files if f.endswith('.smali')]
                smali_analysis["total_smali_files"] += len(smali_files)
                
                # Analyze package distribution
                for file in smali_files:
                    rel_path = os.path.relpath(root, smali_path)
                    if rel_path != ".":
                        package = rel_path.replace(os.path.sep, ".")
                        top_level_package = package.split(".")[0] if "." in package else package
                        
                        if top_level_package not in smali_analysis["package_distribution"]:
                            smali_analysis["package_distribution"][top_level_package] = 0
                        smali_analysis["package_distribution"][top_level_package] += 1
        
        analysis["smali_analysis"] = smali_analysis
        
        # Resource analysis
        res_path = os.path.join(project_dir, "res")
        resource_analysis = {
            "has_resources": os.path.exists(res_path),
            "resource_types": {},
            "total_resource_files": 0
        }
        
        if os.path.exists(res_path):
            try:
                for item in os.listdir(res_path):
                    type_path = os.path.join(res_path, item)
                    if os.path.isdir(type_path):
                        files = [f for f in os.listdir(type_path) if os.path.isfile(os.path.join(type_path, f))]
                        total_size = sum(os.path.getsize(os.path.join(type_path, f)) for f in files)
                        
                        resource_analysis["resource_types"][item] = {
                            "file_count": len(files),
                            "total_size": total_size
                        }
                        resource_analysis["total_resource_files"] += len(files)
            except Exception as e:
                analysis["errors"].append(f"Error analyzing resources: {str(e)}")
        
        analysis["resource_analysis"] = resource_analysis
        
        # Manifest analysis
        manifest_path = os.path.join(project_dir, "AndroidManifest.xml")
        manifest_analysis = {
            "exists": os.path.exists(manifest_path),
            "size": 0,
            "package_name": None,
            "activities": [],
            "permissions": [],
            "services": []
        }
        
        if os.path.exists(manifest_path):
            try:
                manifest_analysis["size"] = os.path.getsize(manifest_path)
                
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    root = ET.fromstring(content)
                    
                    # Extract package name
                    manifest_analysis["package_name"] = root.get("package")
                    
                    # Extract activities
                    for activity in root.findall(".//activity"):
                        name = activity.get("{http://schemas.android.com/apk/res/android}name")
                        if name:
                            manifest_analysis["activities"].append(name)
                    
                    # Extract permissions
                    for perm in root.findall(".//uses-permission"):
                        name = perm.get("{http://schemas.android.com/apk/res/android}name")
                        if name:
                            manifest_analysis["permissions"].append(name)
                    
                    # Extract services
                    for service in root.findall(".//service"):
                        name = service.get("{http://schemas.android.com/apk/res/android}name")
                        if name:
                            manifest_analysis["services"].append(name)
                            
                except ET.ParseError as e:
                    analysis["errors"].append(f"Manifest XML parsing error: {str(e)}")
                    
            except Exception as e:
                analysis["errors"].append(f"Error analyzing manifest: {str(e)}")
        
        analysis["manifest_analysis"] = manifest_analysis
        
        return {
            "success": True,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing project structure: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to analyze project structure: {str(e)}"
        }

@mcp.tool()
async def get_workspace_info() -> Dict:
    """
    Get information about the APKTool MCP server workspace and current projects.
    
    Returns:
        Dictionary with workspace information and project list
    """
    try:
        workspace_info = {
            "workspace_path": WORKSPACE_DIR,
            "workspace_exists": os.path.exists(WORKSPACE_DIR),
            "projects": [],
            "total_projects": 0,
            "total_workspace_size": 0,
            "free_space": 0
        }
        
        if not os.path.exists(WORKSPACE_DIR):
            return {
                "success": False,
                "error": f"Workspace directory does not exist: {WORKSPACE_DIR}",
                "workspace_info": workspace_info
            }
        
        # Get disk usage information
        try:
            import shutil
            total, used, free = shutil.disk_usage(WORKSPACE_DIR)
            workspace_info["free_space"] = free
            workspace_info["total_disk_space"] = total
            workspace_info["used_disk_space"] = used
        except Exception as e:
            logger.warning(f"Could not get disk usage info: {e}")
        
        # Scan for projects
        projects = []
        total_size = 0
        
        for item in os.listdir(WORKSPACE_DIR):
            item_path = os.path.join(WORKSPACE_DIR, item)
            if os.path.isdir(item_path):
                # Check if it looks like an APKTool project
                has_manifest = os.path.exists(os.path.join(item_path, "AndroidManifest.xml"))
                has_apktool_yml = os.path.exists(os.path.join(item_path, "apktool.yml"))
                
                is_apktool_project = has_manifest and has_apktool_yml
                
                # Calculate project size
                project_size = 0
                file_count = 0
                
                try:
                    for root, _, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                project_size += os.path.getsize(file_path)
                                file_count += 1
                            except:
                                pass
                except Exception as e:
                    logger.warning(f"Error calculating size for {item_path}: {e}")
                
                total_size += project_size
                
                project_info = {
                    "name": item,
                    "path": item_path,
                    "is_apktool_project": is_apktool_project,
                    "has_manifest": has_manifest,
                    "has_apktool_yml": has_apktool_yml,
                    "size": project_size,
                    "file_count": file_count,
                    "modified_time": os.path.getmtime(item_path)
                }
                
                # Get additional info if it's a valid project
                if is_apktool_project:
                    try:
                        # Read package name from manifest
                        manifest_path = os.path.join(item_path, "AndroidManifest.xml")
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        root = ET.fromstring(content)
                        project_info["package_name"] = root.get("package")
                        
                        # Count smali directories
                        smali_dirs = [d for d in os.listdir(item_path) 
                                     if d.startswith("smali") and os.path.isdir(os.path.join(item_path, d))]
                        project_info["smali_directories"] = len(smali_dirs)
                        
                    except Exception as e:
                        logger.warning(f"Error getting additional info for {item}: {e}")
                
                projects.append(project_info)
        
        # Sort projects by modification time (newest first)
        projects.sort(key=lambda x: x["modified_time"], reverse=True)
        
        workspace_info["projects"] = projects
        workspace_info["total_projects"] = len(projects)
        workspace_info["total_workspace_size"] = total_size
        workspace_info["apktool_projects"] = len([p for p in projects if p["is_apktool_project"]])
        
        return {
            "success": True,
            "workspace_info": workspace_info
        }
        
    except Exception as e:
        logger.error(f"Error getting workspace info: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get workspace info: {str(e)}"
        }

def main():
    print("=" * 80)
    print("APKTool MCP Server")
    print("By ZinjaCoder (https://github.com/zinja-coder)")
    print("To Report Issues: https://github.com/zinja-coder/apktool-mcp-server/issues")
    print("=" * 80)
    print()
    
    # Display configuration
    print("Configuration:")
    print(f"  Workspace Directory: {WORKSPACE_DIR}")
    print(f"  Default Timeout: {DEFAULT_TIMEOUT}s")
    print(f"  HTTP Mode: {'Enabled' if args.http else 'Disabled'}")
    if args.http:
        print(f"  HTTP Port: {args.port}")
    print()
    
    # Perform initial health check
    print("Performing initial health check...")
    try:
        import asyncio
        health_result = asyncio.run(health_check())
        
        if health_result.get("server_status") == "running":
            print("Server Status: Running")
        else:
            print("Server Status: Error")
        
        if health_result.get("apktool_available"):
            print(f"APKTool Available: {health_result.get('apktool_version', 'Version unknown')}")
        else:
            print("APKTool Not Available")
            print(f"Error: {health_result.get('apktool_error', 'Unknown error')}")
        
        if health_result.get("workspace_exists"):
            print(f"Workspace Directory: {WORKSPACE_DIR}")
        else:
            print(f"Workspace Directory: {WORKSPACE_DIR} (will be created)")
            os.makedirs(WORKSPACE_DIR, exist_ok=True)
        
        # Get workspace info
        workspace_result = asyncio.run(get_workspace_info())
        if workspace_result.get("success"):
            info = workspace_result["workspace_info"]
            print(f"Workspace Projects: {info.get('total_projects', 0)} total")
            print(f"APKTool Projects: {info.get('apktool_projects', 0)}")
            
            if info.get("free_space"):
                free_gb = info["free_space"] / (1024**3)
                print(f"  Free Space: {free_gb:.1f} GB")
        
    except Exception as e:
        print(f"Health check failed: {e}")
    
    print()
    print("Available MCP Tools:")
    tools = [
        "health_check", "decode_apk", "build_apk", "get_manifest", 
        "get_apktool_yml", "list_smali_directories", "list_smali_files", 
        "get_smali_file", "modify_smali_file", "list_resources", 
        "get_resource_file", "modify_resource_file", "search_in_files", 
        "clean_project", "analyze_project_structure", "get_workspace_info"
    ]
    
    for i, tool in enumerate(tools, 1):
        print(f"  {i:2d}. {tool}")
    
    print()
    print("Starting MCP server...")
    
    if args.http:
        print(f"Server will be available at: http://127.0.0.1:{args.port}")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        print("Server running in stdio mode")
        mcp.run()

if __name__ == "__main__":
    main()
