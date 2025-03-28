import os, ast, re, zlib, requests

BOM_UTF8 = '\ufeff'

def read_file_cleanly(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        txt = f.read()
    return txt.lstrip(BOM_UTF8) if txt.startswith(BOM_UTF8) else txt

def write_full_source(out, fp, src):
    out.write(f"# File: {fp}\n{src}\n\n{'='*80}\n\n")

# --- Python UML Generation ---
def generate_uml_from_python(fp, src):
    try:
        tree = ast.parse(src, filename=fp)
    except Exception as e:
        raise SyntaxError(f"AST parse error in {fp}: {e}")
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name): bases.append(base.id)
                elif isinstance(base, ast.Attribute): bases.append(base.attr)
                else: bases.append("UnknownBase")
            fields = []
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            fields.append({'name': t.id, 'type': 'Unknown'})
            methods = []
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    params = [a.arg for a in stmt.args.args if a.arg != "self"]
                    ret = ""
                    if stmt.returns:
                        try: ret = ast.unparse(stmt.returns)
                        except Exception: ret = "Unknown"
                    methods.append({'name': stmt.name, 'params': params, 'return': ret})
            classes.append({'name': node.name, 'bases': bases, 'fields': fields, 'methods': methods})
    uml = "@startuml\n"
    for cls in classes:
        uml += f"class {cls['name']} {{\n"
        for field in cls['fields']:
            uml += f"  - {field['name']} : {field['type']}\n"
        for method in cls['methods']:
            params = ", ".join(method['params'])
            ret = f" : {method['return']}" if method['return'] else ""
            uml += f"  + {method['name']}({params}){ret}\n"
        uml += "}\n"
    for cls in classes:
        for base in cls['bases']:
            if base and base != "object":
                uml += f"{base} <|-- {cls['name']}\n"
    uml += "@enduml\n"
    return uml

# --- C# UML Generation ---
def generate_uml_from_csharp(fp, src):
    class_decl = re.compile(r'^\s*(public|private|protected|internal)?\s*(abstract\s+)?(class|interface|enum)\s+(?P<name>\w+)(?:\s*:\s*(?P<bases>[\w,\s]+))?')
    field_pat = re.compile(r'^\s*(public|private|protected|internal)\s+([\w\<\>\[\]]+)\s+(\w+)\s*(?:=.*)?;')
    method_pat = re.compile(r'^\s*(public|private|protected|internal)\s+([\w\<\>\[\]]+)\s+(\w+)\s*\((?P<params>[^)]*)\)\s*(?:\{|;)')
    classes, current, brace = [], None, 0
    for line in src.splitlines():
        cd = class_decl.match(line)
        if cd:
            if current is not None and brace <= 0:
                classes.append(current); current = None
            current = {'name': cd.group('name'), 'bases': [], 'fields': [], 'methods': []}
            bases_str = cd.group('bases')
            if bases_str: current['bases'] = [b.strip() for b in bases_str.split(',')]
            brace = line.count("{") - line.count("}")
            continue
        if current is not None:
            brace += line.count("{") - line.count("}")
            fm = field_pat.match(line)
            if fm:
                current['fields'].append({'name': fm.group(3), 'type': fm.group(2)})
                continue
            mm = method_pat.match(line)
            if mm:
                params_str = mm.group('params').strip()
                params = []
                if params_str:
                    for p in params_str.split(','):
                        parts = p.strip().split()
                        params.append(f"{parts[1]} : {parts[0]}" if len(parts) >=2 else p.strip())
                current['methods'].append({'name': mm.group(3), 'params': params, 'return': mm.group(2)})
            if brace <= 0:
                classes.append(current); current = None
    if current is not None: classes.append(current)
    uml = "@startuml\n"
    for cls in classes:
        uml += f"class {cls['name']} {{\n"
        for field in cls['fields']:
            uml += f"  - {field['name']} : {field['type']}\n"
        for method in cls['methods']:
            params = ", ".join(method['params'])
            ret = f" : {method['return']}" if method['return'] else ""
            uml += f"  + {method['name']}({params}){ret}\n"
        uml += "}\n"
    for cls in classes:
        for base in cls['bases']:
            if base:
                uml += f"{base} <|-- {cls['name']}\n"
    uml += "@enduml\n"
    return uml

# --- PlantUML Encoding & Visualization ---
def encode6bit(b):
    if b < 10: return chr(48 + b)
    b -= 10
    if b < 26: return chr(65 + b)
    b -= 26
    if b < 26: return chr(97 + b)
    b -= 26
    if b == 0: return '-'
    if b == 1: return '_'
    return '?'

def encode_3bytes(b1, b2, b3):
    c1 = b1 >> 2; c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6); c4 = b3 & 0x3F
    return encode6bit(c1) + encode6bit(c2) + encode6bit(c3) + encode6bit(c4)

def encode_bytes(data):
    return ''.join(encode_3bytes(data[i], data[i+1] if i+1 < len(data) else 0, data[i+2] if i+2 < len(data) else 0) for i in range(0, len(data), 3))

def encode_plantuml(txt):
    comp = zlib.compress(txt.encode('utf-8'))
    comp = comp[2:-4]
    return encode_bytes(comp)

def get_plantuml_svg(uml_txt):
    enc = encode_plantuml(uml_txt)
    url = f"http://www.plantuml.com/plantuml/svg/{enc}"
    r = requests.get(url)
    if r.status_code == 200: return r.text
    raise Exception(f"Error fetching UML SVG: HTTP {r.status_code}")

def generate_uml_visualization(uml_txt, out_svg):
    try:
        svg = get_plantuml_svg(uml_txt)
        with open(out_svg, 'w', encoding='utf-8') as f: f.write(svg)
        print(f"SVG written to {out_svg}")
    except Exception as e:
        print(f"Failed to generate SVG: {e}")

def extract_uml_body(uml_txt):
    return "\n".join(line for line in uml_txt.splitlines() if not line.strip().startswith("@startuml") and not line.strip().startswith("@enduml"))

# --- Main Processing ---
def dump_files_to_uml(project_name, src_dir, out_full, out_comb_svg):
    if not os.path.isdir(src_dir):
        print(f"Error: '{src_dir}' is not a valid directory."); return
    combined = []
    with open(out_full, 'w', encoding='utf-8') as full_out:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in {'__pycache__','.ipynb_checkpoints','.git'}]
            for file in files:
                if file.endswith('.py') or file.endswith('.cs'):
                    fp = os.path.join(root, file)
                    print(f"Processing: {fp}")
                    if not os.path.isfile(fp): continue
                    try:
                        src = read_file_cleanly(fp)
                        if not src.strip(): continue
                        write_full_source(full_out, fp, src)
                        uml_diag = generate_uml_from_python(fp, src) if file.endswith('.py') else generate_uml_from_csharp(fp, src)
                        body = extract_uml_body(uml_diag)
                        if body.strip():
                            combined.append(f"' From file: {fp}\n{body}")
                    except Exception as e:
                        print(f"Error processing {fp}: {e}")
    if combined:
        comb_uml = "@startuml\n" + "\n".join(combined) + "\n@enduml\n"
        with open(f"{project_name}_combined_uml.txt", 'w', encoding='utf-8') as f:
            f.write(comb_uml)
        print(f"Combined UML text written to {project_name}_combined_uml.txt")
        generate_uml_visualization(comb_uml, out_comb_svg)
    else:
        print("No UML bodies generated.")

# --- Configuration ---
# Paste your source directory here and set the project name.
project_name = "UMLGenerator"
source_directory = f"/Users/benbradley/Desktop/CS_Classwork/UTRA/burner/cloned_analysis/{project_name}"

out_full_source_file = f"{project_name}_full_source.txt"
out_combined_svg = f"{project_name}_combined_uml.svg"

if __name__ == '__main__':
    dump_files_to_uml(project_name, source_directory, out_full_source_file, out_combined_svg)
    print("UML generation complete.")
