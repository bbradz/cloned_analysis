import os
import ast

def dump_py_files_to_txt(source_dir, output_text_file, output_decls_file):
    if not os.path.isdir(source_dir):
        print(f"Error: source directory '{source_dir}' does not exist or is not a directory.")
        return

    with open(output_text_file, 'w', encoding='utf-8') as full_out_f, \
         open(output_decls_file, 'w', encoding='utf-8') as decls_out_f:

        for root, dirs, files in os.walk(source_dir):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.ipynb_checkpoints', '.git'}]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    print(f"Parsing: {file_path}")

                    if not os.path.isfile(file_path):
                        print(f"Skipping non-file: {file_path}")
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            source = f.read()

                            if not source.strip():
                                print(f"Skipping empty file: {file_path}")
                                continue

                            # Write full source
                            full_out_f.write(f"# File: {file_path}\n")
                            full_out_f.write(source)
                            full_out_f.write("\n\n" + "="*80 + "\n\n")

                            # Parse and reconstruct declarations with 'pass'
                            tree = ast.parse(source, filename=file_path)
                            decl_lines = [f"# File: {file_path}\n"]

                            class DeclarationTransformer(ast.NodeTransformer):
                                def visit_FunctionDef(self, node):
                                    node.body = [ast.Pass()]
                                    return node

                                def visit_AsyncFunctionDef(self, node):
                                    node.body = [ast.Pass()]
                                    return node

                                def visit_ClassDef(self, node):
                                    self.generic_visit(node)
                                    return node

                            tree = DeclarationTransformer().visit(tree)
                            ast.fix_missing_locations(tree)

                            decl_source = ast.unparse(tree)
                            decl_lines.append(decl_source)
                            decl_lines.append("\n\n" + "="*80 + "\n\n")

                            decls_out_f.writelines(decl_lines)

                    except Exception as e:
                        print(f"Could not read or parse {file_path}: {e}")

# Example usage:
name = 'AI-Feynman'
dump_py_files_to_txt(
    f'/Users/benbradley/Desktop/CS_Classwork/UTRA/burner/cloned_analysis_old/{name}', 
    f'{name}_code.txt', 
    f'{name}_declarations.txt')
