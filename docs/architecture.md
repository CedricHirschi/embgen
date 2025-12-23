# embgen Architecture

This document describes the architecture and module structure of the embgen package.

## Package Overview

```mermaid
flowchart TB
    subgraph User["User Interaction"]
        CLI["CLI<br/>(cli.py)"]
        YAML["YAML Config<br/>(*.yml)"]
    end

    subgraph Core["Core Generation"]
        CG["CodeGenerator<br/>(generator.py)"]
        Templates["Template Utilities<br/>(templates.py)"]
    end

    subgraph Discovery["Discovery System"]
        Disc["discover_domains()<br/>(discovery.py)"]
        Detect["detect_domain()<br/>(discovery.py)"]
    end

    subgraph Models["Data Models"]
        BaseConfig["BaseConfig<br/>(Pydantic)"]
        Enum["Enum<br/>(Pydantic)"]
        TI["TemplateInfo<br/>(dataclass)"]
        MG["MultifileGroup<br/>(dataclass)"]
    end

    subgraph Domains["Domain Generators"]
        DG["DomainGenerator ABC<br/>(domains/__init__.py)"]
        CMD["CommandsGenerator<br/>(domains/commands/)"]
        REG["RegistersGenerator<br/>(domains/registers/)"]
        User_Domain["User Domains<br/>(EMBGEN_DOMAINS_DIR)"]
    end

    subgraph Output["Generated Files"]
        Header["*.h"]
        Python["*.py"]
        Markdown["*.md"]
        Other["Other formats"]
    end

    CLI --> |"1. Parse args"| Disc
    CLI --> |"2. Load YAML"| YAML
    Disc --> |"Find domains"| DG
    DG --> CMD
    DG --> REG
    DG --> User_Domain
    CLI --> |"3. Create"| CG
    CG --> |"4. Parse YAML"| YAML
    CG --> |"5. Validate"| DG
    CG --> |"6. Render"| Templates
    Templates --> |"Jinja2"| Output
    CG --> |"7. Post-generate"| DG
```

## Module Responsibilities

```mermaid
classDiagram
    class cli {
        +main()
        +add_template_flags()
        +build_parser()
    }
    
    class discovery {
        +BUILTIN_DOMAINS_PATH
        +EMBGEN_DOMAINS_DIR_ENV
        +discover_domains()
        +detect_domain()
    }
    
    class generator {
        +CodeGenerator
    }
    
    class templates {
        +FILE_TYPES
        +file_type()
        +get_env()
        +parse_template_name()
        +discover_templates()
    }
    
    class models {
        +BaseConfig
        +Enum
        +TemplateInfo
        +MultifileGroup
    }
    
    class scaffold {
        +scaffold_domain()
    }
    
    class DomainGenerator {
        <<abstract>>
        +name: str
        +description: str
        +templates_path: Path
        +detect(data) bool
        +validate(data) BaseConfig
        +render(config, template) str
        +post_generate()
    }
    
    class CodeGenerator {
        +generator: DomainGenerator
        +output_path: Path
        +env: Environment
        +parse_yaml(path) dict
        +validate(data) BaseConfig
        +ensure_output_dir() Path
        +render_to_file()
        +render_multifile_group()
        +generate()
        +generate_from_file()
    }

    cli --> discovery : imports
    cli --> generator : uses
    cli --> templates : uses
    cli --> scaffold : uses
    generator --> DomainGenerator : uses
    generator --> templates : uses
    generator --> models : uses
    DomainGenerator --> models : extends BaseConfig
```

## Generation Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as cli.py
    participant Disc as discovery.py
    participant Gen as CodeGenerator
    participant Domain as DomainGenerator
    participant Tmpl as templates.py
    participant FS as File System

    User->>CLI: embgen commands config.yml -h -p
    CLI->>Disc: discover_domains()
    Disc-->>CLI: {commands: CommandsGen, registers: RegistersGen}
    CLI->>Disc: detect_domain(yaml_data) [if auto-detect]
    CLI->>Gen: new CodeGenerator(domain, output_path)
    CLI->>Gen: generate_from_file(config.yml, templates)
    Gen->>FS: parse YAML file
    Gen->>Domain: validate(data)
    Domain-->>Gen: CommandsConfig
    Gen->>Gen: ensure_output_dir()
    
    loop For each template
        Gen->>Domain: render(config, template)
        Domain->>Tmpl: Jinja2 rendering
        Tmpl-->>Domain: rendered content
        Domain-->>Gen: content string
        Gen->>FS: write output file
    end
    
    Gen->>Domain: post_generate(output_path, generated_exts)
    Domain->>FS: copy extra files (e.g., commands_base.py)
    Gen-->>CLI: list of generated filenames
    CLI-->>User: Success message
```

## Domain Structure

```mermaid
graph LR
    subgraph BuiltIn["Built-in Domains"]
        subgraph Commands["domains/commands/"]
            CMD_Init["__init__.py"]
            CMD_Gen["generator.py"]
            CMD_Mod["models.py"]
            CMD_Tmpl["templates/"]
        end
        
        subgraph Registers["domains/registers/"]
            REG_Init["__init__.py"]
            REG_Gen["generator.py"]
            REG_Mod["models.py"]
            REG_Tmpl["templates/"]
        end
    end
    
    subgraph UserDomains["User Domains (optional)"]
        USR_Dir["EMBGEN_DOMAINS_DIR/"]
        USR_Custom["custom_domain/"]
    end
    
    Discovery["discovery.py"]
    
    Discovery -->|"scan"| BuiltIn
    Discovery -->|"scan (override)"| UserDomains
```

## Multifile Template Support

```mermaid
flowchart LR
    subgraph Templates["Template Files"]
        Single["template.h.j2<br/>template.py.j2"]
        Multi["template.c_multi.h.j2<br/>template.c_multi.c.j2"]
        MultiSuffix["template.sv_multi.sv.1.j2<br/>template.sv_multi.sv.2.j2"]
    end
    
    subgraph Parsing["parse_template_name()"]
        Parse1["(None, 'h', None)"]
        Parse2["('c', 'h', None)<br/>('c', 'c', None)"]
        Parse3["('sv', 'sv', '1')<br/>('sv', 'sv', '2')"]
    end
    
    subgraph Output["Generated Files"]
        Out1["config.h"]
        Out2["config.h<br/>config.c"]
        Out3["config_1.sv<br/>config_2.sv"]
    end
    
    Single --> Parse1 --> Out1
    Multi --> Parse2 --> Out2
    MultiSuffix --> Parse3 --> Out3
```

## Key Design Patterns

1. **Abstract Factory**: `DomainGenerator` ABC defines the interface, concrete implementations (CommandsGenerator, RegistersGenerator) are discovered dynamically.

2. **Strategy Pattern**: Each domain implements its own validation and rendering strategy.

3. **Plugin Architecture**: User domains can be added via `EMBGEN_DOMAINS_DIR` environment variable without modifying core code.

4. **Separation of Concerns**:
   - `discovery.py`: Finding and loading domains
   - `generator.py`: Orchestrating the generation workflow
   - `templates.py`: Template utilities and parsing
   - `models.py`: Shared data structures
   - `cli.py`: Command-line interface only
