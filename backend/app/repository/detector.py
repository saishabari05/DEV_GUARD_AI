import os
import json

def detect_repository_metadata(workspace_path: str) -> dict:
    """
    Detects language, framework, test command, and project structure from workspace contents.
    Returns clean, safe relative metadata without exposing host filesystem paths.
    """
    workspace_path = os.path.abspath(workspace_path)
    if not os.path.isdir(workspace_path):
        return {
            "language": "Unknown",
            "framework": "Unknown",
            "test_framework": "Unknown",
            "test_command": "Not detected",
            "file_count": 0,
            "source_directories": [],
            "test_directories": []
        }

    file_count = 0
    all_files = []
    
    for root, dirs, files in os.walk(workspace_path):
        # Ignore common hidden or virtual directories
        dirs[:] = [d for d in dirs if d not in [".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"]]
        for file in files:
            file_count += 1
            rel_path = os.path.relpath(os.path.join(root, file), workspace_path).replace("\\", "/")
            all_files.append(rel_path)

    language = "Unknown"
    framework = "Unknown"
    test_framework = "Unknown"
    test_command = "Not detected"
    source_dirs = set()
    test_dirs = set()

    # Detect directories
    for f in all_files:
        parts = f.split("/")
        if len(parts) > 1:
            if parts[0] in ["app", "src", "lib", "main"]:
                source_dirs.add(parts[0])
            if parts[0] in ["tests", "test", "spec"]:
                test_dirs.add(parts[0])

    # 1. File checks
    has_py_files = any(f.endswith(".py") for f in all_files)
    req_file = os.path.join(workspace_path, "requirements.txt")
    pyproject = os.path.join(workspace_path, "pyproject.toml")
    setup_py = os.path.join(workspace_path, "setup.py")
    setup_cfg = os.path.join(workspace_path, "setup.cfg")
    pytest_ini = os.path.join(workspace_path, "pytest.ini")

    package_json = os.path.join(workspace_path, "package.json")
    tsconfig = os.path.join(workspace_path, "tsconfig.json")
    has_js_ts_files = any(f.endswith((".js", ".jsx", ".ts", ".tsx")) for f in all_files)

    pom_xml = os.path.join(workspace_path, "pom.xml")
    build_gradle = os.path.join(workspace_path, "build.gradle")
    build_gradle_kts = os.path.join(workspace_path, "build.gradle.kts")
    has_java_files = any(f.endswith(".java") for f in all_files)

    # 2. Determine Language & Framework & Test Command
    if has_py_files or os.path.exists(req_file) or os.path.exists(pyproject) or os.path.exists(setup_py) or os.path.exists(setup_cfg) or os.path.exists(pytest_ini):
        language = "Python"
        
        # Test command discovery for Python
        if os.path.exists(pytest_ini) or any("test" in f for f in all_files if f.endswith(".py")):
            test_framework = "pytest"
            test_command = "pytest"
        else:
            test_framework = "Unknown"
            test_command = "pytest" if has_py_files else "Not detected"

        # Framework discovery from dependencies or content
        req_content = ""
        if os.path.exists(req_file):
            try:
                with open(req_file, "r", encoding="utf-8", errors="ignore") as rf:
                    req_content = rf.read().lower()
            except Exception:
                pass

        if os.path.exists(pyproject):
            try:
                with open(pyproject, "r", encoding="utf-8", errors="ignore") as pf:
                    req_content += pf.read().lower()
            except Exception:
                pass

        if "flask" in req_content:
            framework = "Flask"
        elif "fastapi" in req_content:
            framework = "FastAPI"
        elif "django" in req_content:
            framework = "Django"
        else:
            framework = "Unknown"

    elif os.path.exists(package_json) or os.path.exists(tsconfig) or has_js_ts_files:
        has_ts = any(f.endswith((".ts", ".tsx")) for f in all_files) or os.path.exists(tsconfig)
        language = "TypeScript" if has_ts else "JavaScript"

        if os.path.exists(package_json):
            try:
                with open(package_json, "r", encoding="utf-8", errors="ignore") as pf:
                    pkg_data = json.load(pf)
                    deps = pkg_data.get("dependencies", {})
                    dev_deps = pkg_data.get("devDependencies", {})
                    all_deps = {**deps, **dev_deps}
                    
                    if "react" in all_deps:
                        framework = "React"
                    elif "express" in all_deps:
                        framework = "Express"
                    else:
                        framework = "Unknown"

                    scripts = pkg_data.get("scripts", {})
                    if "test" in scripts:
                        test_command = "npm test"
                    elif "test:unit" in scripts:
                        test_command = "npm run test:unit"
                    else:
                        test_command = "npm test"
            except Exception:
                test_command = "npm test"
        else:
            test_command = "Not detected"

    elif os.path.exists(pom_xml) or os.path.exists(build_gradle) or os.path.exists(build_gradle_kts) or has_java_files:
        language = "Java"
        
        # Check Spring dependency/config
        pom_content = ""
        if os.path.exists(pom_xml):
            try:
                with open(pom_xml, "r", encoding="utf-8", errors="ignore") as f:
                    pom_content = f.read().lower()
            except Exception:
                pass

        if "spring" in pom_content:
            framework = "Spring"
        else:
            framework = "Unknown"

        if os.path.exists(pom_xml):
            test_command = "mvn test"
            test_framework = "JUnit"
        elif os.path.exists(build_gradle) or os.path.exists(build_gradle_kts):
            test_command = "./gradlew test"
            test_framework = "JUnit"
        else:
            test_command = "Not detected"
            test_framework = "Unknown"

    return {
        "repository_name": os.path.basename(workspace_path),
        "repository_url": None,
        "local_workspace_path": workspace_path,
        "language": language,
        "framework": framework,
        "test_framework": test_framework,
        "test_command": test_command,
        "file_count": file_count,
        "source_directories": sorted(list(source_dirs)),
        "test_directories": sorted(list(test_dirs))
    }


