# 🚀 Oracle Agent Vercel Deployment Guide

## 📋 Overview

This guide provides step-by-step instructions for deploying Oracle Agent on Vercel using the serverless-compatible configuration.

## 🔧 Prerequisites

- Vercel account (free tier is sufficient)
- GitHub repository with Oracle Agent code
- Basic understanding of serverless functions

## 📁 File Structure

The Vercel deployment uses this structure:

```
oracle-agent/
├── api/
│   ├── index.py          # Vercel serverless function entrypoint
│   └── vercel_app.py      # Vercel-compatible Flask app
├── vercel.json            # Vercel configuration
├── vercel_requirements.txt # Python dependencies for Vercel
└── [other project files]
```

## 🚀 Deployment Steps

### 1. Prepare Your Repository

Ensure your repository has the Vercel configuration files:

```bash
# Check if files exist
ls -la vercel.json api/
```

### 2. Connect to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Link your project
cd /path/to/oracle-agent
vercel link
```

### 3. Configure Environment Variables

Set up environment variables in Vercel dashboard or CLI:

```bash
# Set environment variables
vercel env add ORACLE_DEMO_MODE
# When prompted, enter: true

vercel env add FORCE_HTTPS
# When prompted, enter: false

vercel env add SECRET_KEY
# When prompted, enter a secure random string
```

### 4. Deploy to Vercel

```bash
# Deploy to Vercel
vercel --prod

# Or for preview deployment
vercel
```

## 🔧 Configuration Details

### vercel.json

The `vercel.json` file configures:

- **Serverless Functions**: Routes requests to `api/index.py`
- **Rewrites**: Directs all traffic to the serverless function
- **Build Configuration**: Uses Python runtime
- **Environment Variables**: Sets demo mode and other settings

### API Structure

#### `api/index.py`
- Vercel serverless function entrypoint
- Converts Vercel requests to WSGI format
- Handles error cases gracefully

#### `api/vercel_app.py`
- Simplified Flask application for Vercel
- Professional web interface without Socket.IO
- Demo mode with interactive features
- Multiple API endpoints for system status

## 🌐 Features Available on Vercel

### ✅ Available Features
- **Professional Web Interface**: Luxury GUI design
- **System Status**: Health checks and monitoring
- **Demo Chat Interface**: Interactive demo functionality
- **API Endpoints**: RESTful API for system information
- **Enterprise Feature Showcase**: Demonstrates all capabilities
- **Responsive Design**: Works on all devices

### ⚠️ Limitations on Vercel
- **No Real-time Features**: Socket.IO not supported in serverless
- **Demo Mode Only**: Full AI features require proper credentials
- **Limited Background Processing**: Serverless execution limits
- **No File Upload**: Serverless functions have storage limitations

## 📊 API Endpoints

### Main Interface
- **GET /**: Professional web interface
- **GET /api/health**: System health check
- **GET /api/status**: Detailed system status

### Demo Features
- **POST /api/chat**: Interactive chat demo
- **GET /api/workflows**: Workflow management demo
- **GET /api/agents**: Agent status demo
- **GET /api/plugins**: Plugin management demo

## 🔍 Testing Your Deployment

### Health Check
```bash
# Test health endpoint
curl https://your-app.vercel.app/api/health

# Expected response
{
  "status": "healthy",
  "service": "oracle-agent-vercel",
  "version": "5.0.0-hardened",
  "timestamp": "2026-03-25T12:00:00Z",
  "demo_mode": true
}
```

### System Status
```bash
# Test status endpoint
curl https://your-app.vercel.app/api/status

# Expected response includes system information, capabilities, and feature status
```

### Interactive Demo
1. Visit `https://your-app.vercel.app`
2. Use the interactive chat interface
3. Explore the feature showcase
4. Test API endpoints directly

## 🛠️ Customization

### Modifying the Interface

Edit `api/vercel_app.py` to customize:

- **HTML Template**: Modify the `HTML_TEMPLATE` variable
- **API Responses**: Update endpoint handlers
- **Styling**: Change CSS in the template
- **Features**: Add or remove demo features

### Adding Custom Endpoints

```python
@app.route('/api/custom', methods=['GET', 'POST'])
def custom_endpoint():
    """Custom API endpoint."""
    return jsonify({
        'success': True,
        'message': 'Custom functionality',
        'timestamp': datetime.now().isoformat()
    })
```

### Environment Configuration

Add environment variables in Vercel dashboard:

1. Go to Vercel dashboard → Project → Settings → Environment Variables
2. Add new variables as needed
3. Redeploy to apply changes

## 🔒 Security Considerations

### Vercel Security
- **HTTPS Only**: Automatic SSL certificates
- **Isolation**: Serverless function isolation
- **Rate Limiting**: Built-in DDoS protection
- **Environment Variables**: Secure secret management

### Application Security
- **Input Validation**: All inputs validated
- **Error Handling**: Graceful error responses
- **Demo Mode**: No sensitive operations in demo
- **CORS**: Proper cross-origin configuration

## 📈 Performance Optimization

### Vercel Optimizations
- **Edge Caching**: Static content cached globally
- **Function Caching**: Reuse function instances
- **Compression**: Automatic response compression
- **CDN**: Global content delivery

### Application Optimizations
- **Lightweight Dependencies**: Minimal Python packages
- **Efficient Code**: Optimized for serverless execution
- **Fast Responses**: Quick API responses
- **Resource Management**: Proper memory usage

## 🔧 Troubleshooting

### Common Issues

#### Build Failures
```bash
# Check build logs
vercel logs

# Common solutions:
# - Check syntax errors in Python files
# - Verify dependencies in vercel_requirements.txt
# - Ensure all imports are correct
```

#### Runtime Errors
```bash
# Check function logs
vercel logs --filter=api/index.py

# Common solutions:
# - Verify environment variables
# - Check import paths
# - Ensure proper error handling
```

#### Performance Issues
```bash
# Monitor performance
vercel logs --filter=api/index.py --since=1h

# Optimization tips:
# - Reduce response sizes
# - Optimize database queries
# - Use caching strategies
```

### Debug Mode

Enable debug logging:

```bash
# Set debug environment variable
vercel env add ORACLE_LOG_LEVEL
# When prompted, enter: DEBUG

# Redeploy with debug mode
vercel --prod
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Repository has all required files
- [ ] `vercel.json` is properly configured
- [ ] `api/` directory exists with required files
- [ ] Dependencies are specified in `vercel_requirements.txt`
- [ ] Environment variables are configured

### Post-Deployment
- [ ] Health check passes
- [ ] Main interface loads correctly
- [ ] API endpoints respond properly
- [ ] Demo features work as expected
- [ ] Error handling works gracefully

### Monitoring
- [ ] Set up Vercel analytics
- [ ] Monitor function performance
- [ ] Check error logs regularly
- [ ] Set up alerts for issues

## 🚀 Next Steps

### Full Deployment
For production deployment with full AI capabilities:

1. **Self-Hosting**: Deploy on your own infrastructure
2. **Cloud Platform**: Use AWS, GCP, or Azure
3. **Container Deployment**: Use Docker/Kubernetes
4. **Enterprise Setup**: Contact for enterprise deployment

### Custom Development
- **Plugin Development**: Create custom plugins
- **Integration Development**: Add external integrations
- **UI Customization**: Customize the interface
- **API Development**: Extend API functionality

## 📞 Support

### Vercel Support
- [Vercel Documentation](https://vercel.com/docs)
- [Vercel Community](https://vercel.com/community)
- [Vercel Status](https://vercel.com/status)

### Oracle Agent Support
- [GitHub Issues](https://github.com/oracle-agent/oracle-agent/issues)
- [Documentation](https://oracle-agent.com/docs)
- [Community](https://github.com/oracle-agent/oracle-agent/discussions)

---

## 🎉 Success!

Your Oracle Agent is now deployed on Vercel! 

**What you have:**
- ✅ Professional web interface
- ✅ Demo functionality
- ✅ API endpoints
- ✅ Enterprise feature showcase
- ✅ Global CDN deployment
- ✅ SSL certificates
- ✅ Automatic scaling

**Next steps:**
1. Share your Vercel URL
2. Explore the demo interface
3. Test the API endpoints
4. Consider full deployment for production use

**🚀 Oracle Agent on Vercel - Enterprise AI Demo Platform!**
