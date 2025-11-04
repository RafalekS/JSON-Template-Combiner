# Docker Compose Support - Complete Guide

The JSON Template Combiner now supports converting Docker Compose YAML files into Portainer templates, making it easy to migrate existing Docker Compose setups to Portainer or create templates from compose files.

## 🚀 **How It Works**

### **Automatic Detection**
The application automatically detects Docker Compose files by:
- File extension: `.yml`, `.yaml`
- Content structure: presence of `services` section
- Docker Compose fields: `version`, `services`, `networks`, `volumes`

### **Service-to-Template Conversion**
Each service in your Docker Compose file becomes a separate Portainer template:

```yaml
# docker-compose.yml
version: '3.8'
services:
  nginx:
    image: nginx:latest
    ports: ["80:80"]
  mysql:
    image: mysql:8.0
    ports: ["3306:3306"]
```

**Becomes →** 2 separate Portainer templates: "Nginx" and "Mysql"

## 📋 **Field Mapping Reference**

### **Basic Service Information**
| Docker Compose | Portainer Template | Notes |
|----------------|-------------------|-------|
| Service name | `title` | Converted to Title Case |
| `container_name` | `title` | Used if present, otherwise service name |
| `image` | `image` | Direct mapping |
| `restart` | `restart_policy` | Mapped to Portainer values |

### **Port Mappings**
| Docker Compose | Portainer Template |
|----------------|-------------------|
| `"80:80"` | `{"Port 80": "80/tcp"}` |
| `"8080:80"` | `{"Port 80": "80/tcp"}` |
| `ports: ["80:80/udp"]` | `{"Port 80": "80/udp"}` |

**Advanced Port Formats**:
```yaml
# Docker Compose expanded format
ports:
  - target: 80
    published: 8080
    protocol: tcp
```
**Becomes →** `{"Port 80": "80/tcp"}`

### **Volume Mappings**
| Docker Compose | Portainer Template |
|----------------|-------------------|
| `"./data:/app/data"` | `{"container": "/app/data", "bind": "!data/data"}` |
| `"myvolume:/data"` | `{"container": "/data", "bind": "!data/myvolume"}` |
| `"/host/path:/container/path"` | `{"container": "/container/path", "bind": "/host/path"}` |

**Volume Conversion Rules**:
- Relative paths (`./`) → `!data/` prefix
- Named volumes → `!data/{volume_name}`
- Absolute paths → kept as-is

### **Environment Variables**
| Docker Compose | Portainer Template |
|----------------|-------------------|
| `"VAR=value"` | `{"name": "VAR", "default": "value"}` |
| `"VAR"` | `{"name": "VAR"}` |
| `{VAR: value}` | `{"name": "VAR", "default": "value"}` |

**Both formats supported**:
```yaml
# Array format
environment:
  - MYSQL_ROOT_PASSWORD=secret
  - MYSQL_DATABASE=myapp

# Object format  
environment:
  MYSQL_ROOT_PASSWORD: secret
  MYSQL_DATABASE: myapp
```

### **Restart Policies**
| Docker Compose | Portainer Template |
|----------------|-------------------|
| `no` | `no` |
| `always` | `always` |
| `on-failure` | `on-failure` |
| `unless-stopped` | `unless-stopped` |

## 🎯 **Smart Category Detection**

The application automatically assigns categories based on service names and image names:

| Detected Keywords | Category |
|------------------|----------|
| mysql, postgres, mongodb, redis, mariadb | `database` |
| nginx, apache, httpd, caddy | `webserver` |
| plex, jellyfin, sonarr, radarr | `media` |
| traefik, nginx-proxy, haproxy | `networking` |
| prometheus, grafana, influxdb | `monitoring` |
| node, python, php, ruby | `development` |
| nextcloud, owncloud, seafile | `storage` |
| vault, keycloak, authelia | `security` |

**Fallback**: If no keywords match, assigns `tools` category.

## 📝 **Example Conversions**

### **Example 1: Simple Web Server**

**Input (docker-compose.yml)**:
```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    container_name: my-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./conf:/etc/nginx/conf.d:ro
    restart: unless-stopped
    environment:
      - NGINX_HOST=example.com
```

**Output (Portainer Template)**:
```json
{
  "title": "My-nginx",
  "description": "Container service: nginx",
  "image": "nginx:alpine",
  "platform": "linux",
  "restart_policy": "unless-stopped",
  "categories": ["webserver"],
  "env": [
    {"name": "NGINX_HOST", "default": "example.com"}
  ],
  "ports": [
    {"Port 80": "80/tcp"},
    {"Port 443": "443/tcp"}
  ],
  "volumes": [
    {"container": "/usr/share/nginx/html", "bind": "!data/html"},
    {"container": "/etc/nginx/conf.d", "bind": "!data/conf"}
  ]
}
```

### **Example 2: Database with Named Volume**

**Input (docker-compose.yml)**:
```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: supersecret
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wpuser
      MYSQL_PASSWORD: wppass
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

volumes:
  mysql_data:
```

**Output (Portainer Template)**:
```json
{
  "title": "Mysql",
  "description": "Container service: mysql",
  "image": "mysql:8.0",
  "platform": "linux",
  "restart_policy": "always",
  "categories": ["database"],
  "env": [
    {"name": "MYSQL_ROOT_PASSWORD", "default": "supersecret"},
    {"name": "MYSQL_DATABASE", "default": "wordpress"},
    {"name": "MYSQL_USER", "default": "wpuser"},
    {"name": "MYSQL_PASSWORD", "default": "wppass"}
  ],
  "ports": [
    {"Port 3306": "3306/tcp"}
  ],
  "volumes": [
    {"container": "/var/lib/mysql", "bind": "!data/mysql_data"}
  ]
}
```

### **Example 3: Multi-Service Application**

**Input (docker-compose.yml)**:
```yaml
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    depends_on:
      - api
    
  api:
    image: node:18-alpine
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
      DATABASE_URL: postgres://user:pass@db:5432/app
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Output**: 3 separate Portainer templates:
1. **"Web"** (nginx) - webserver category
2. **"Api"** (node) - development category  
3. **"Db"** (postgres) - database category

## 🔧 **Usage Instructions**

### **Step 1: Prepare Your Compose File**
Ensure your `docker-compose.yml` or `compose.yaml` file is properly formatted and contains services with images.

### **Step 2: Load in Application**
1. **Sources Tab** → Click "Add Template File (JSON/YAML/Compose)"
2. **File Dialog** → Select your compose file
3. **File Types** → Choose "Docker Compose" filter or "YAML files"
4. **Load** → Click "Load & Process Sources"

### **Step 3: Review Conversion**
1. **Preview Tab** → Review processing summary
2. **Summary** → See "X templates (converted)" for compose files
3. **Edit Templates Tab** → Browse individual converted templates
4. **Modify** → Edit any template if needed in Manual Entry tab

### **Step 4: Generate and Export**
1. **Preview Tab** → Click "Generate Final Template"
2. **Review** → Check combined templates
3. **Save Tab** → Export final `templates.json`

## ⚠️ **Limitations and Notes**

### **Not Converted**:
- **Build contexts** (services without `image` field)
- **Networks** (not directly applicable to Portainer templates)
- **Dependencies** (`depends_on`, `links` - handled by Portainer stack deployment)
- **Healthchecks** (not standard in Portainer templates)
- **Deploy** configurations (Docker Swarm specific)

### **Automatic Adjustments**:
- **Service names** converted to Title Case for template titles
- **Relative paths** prefixed with `!data/` for Portainer compatibility
- **Named volumes** converted to `!data/{volume_name}` format
- **Categories** automatically assigned based on image analysis

### **Manual Review Recommended**:
- **Environment variable values** (especially secrets/passwords)
- **Volume paths** (ensure they make sense in Portainer context)
- **Port mappings** (verify host ports are appropriate)
- **Template descriptions** (auto-generated, may need customization)

## 🎯 **Best Practices**

### **Before Conversion**:
1. **Clean up** unnecessary services (like build-only containers)
2. **Document** complex configurations in service labels
3. **Use** descriptive service names (they become template titles)
4. **Organize** related services in separate compose files if needed

### **After Conversion**:
1. **Review** generated templates in Edit Templates tab
2. **Customize** descriptions and categories as needed
3. **Test** templates in Portainer before widespread use
4. **Document** any manual changes made

### **Security Considerations**:
1. **Remove** or parameterize hardcoded passwords
2. **Use** environment variables for sensitive data
3. **Review** volume mappings for security implications
4. **Update** default values to be more generic

## 🔄 **Integration with Other Features**

Docker Compose templates integrate seamlessly with other application features:

### **Template Editing**:
- **Browse** converted templates in Edit Templates tab
- **Edit** any converted template in Manual Entry tab
- **Clone** templates to create variations

### **Category Management**:
- **Automatic** categories are added to the dropdown
- **Custom** categories can be added to converted templates
- **Refresh** categories after loading compose files

### **Deduplication**:
- **Participate** in 70% similarity checking with other templates
- **Architecture** detection works with converted templates
- **Smart merging** with templates from other sources

## 📊 **Supported Compose Versions**

The converter supports Docker Compose file format versions:
- ✅ **Version 2.x** (legacy format)
- ✅ **Version 3.x** (current standard)
- ✅ **No version specified** (assumes modern format)

**Recommendation**: Use version 3.8 or later for best compatibility.

## 🛠️ **Troubleshooting**

### **Common Issues**:

**"Invalid Docker Compose format"**:
- Check YAML syntax (indentation, colons, dashes)
- Ensure `services` section exists
- Verify file is valid YAML

**"No templates generated"**:
- Services must have `image` field (build-only services skipped)
- Check that services section contains valid service definitions

**"Port conversion issues"**:
- Use string format: `"80:80"` not `80:80`
- Include protocol if needed: `"53:53/udp"`

**"Volume path problems"**:
- Use forward slashes even on Windows
- Relative paths are converted to `!data/` prefix
- Named volumes are converted to `!data/{name}`

### **Debug Steps**:
1. **Validate YAML** using online YAML validator
2. **Check logs** in application status messages
3. **View JSON** of converted templates using "View JSON" button
4. **Test** original compose file with `docker-compose config`

## 🎉 **Benefits**

### **Migration from Docker Compose to Portainer**:
- **Quick conversion** of existing setups
- **Preserve** configuration and relationships
- **Template library** for reusable deployments
- **Share** configurations across teams

### **Template Development**:
- **Start** with familiar compose syntax
- **Generate** Portainer templates automatically
- **Customize** as needed in the GUI
- **Version control** compose files easily

### **Learning Tool**:
- **Understand** Portainer template structure
- **See** how compose concepts map to templates
- **Bridge** gap between compose and Portainer workflows

---

**Docker Compose support makes the JSON Template Combiner a complete solution for container template management, supporting migration from compose workflows to Portainer templates while maintaining all the powerful features for template customization and management.** 🚀
