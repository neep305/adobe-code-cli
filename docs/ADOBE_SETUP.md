# Adobe Developer Console Setup Guide

This guide walks you through setting up OAuth Server-to-Server credentials for Adobe Experience Platform API access.

## Prerequisites

- Adobe Experience Platform license
- Adobe Developer Console access
- Admin or Developer role in your Adobe organization

## Step-by-Step Setup

### 1. Access Adobe Developer Console

1. Navigate to [Adobe Developer Console](https://developer.adobe.com/console)
2. Sign in with your Adobe ID
3. Select your organization from the top-right dropdown

### 2. Create a New Project

1. Click **"Create new project"** or select existing project
2. Click **"Add API"** button
3. Search for **"Experience Platform API"**
4. Click **"Next"**

### 3. Configure OAuth Server-to-Server

1. Select **"OAuth Server-to-Server"** as credential type
   - ⚠️ **Do NOT use** "Service Account (JWT)" - it's deprecated as of 2024
2. Click **"Next"**

### 4. Select Product Profiles

Choose the appropriate product profiles based on your use case:

**Required for this agent:**
- ✅ **AEP - Data Management** - For schema and dataset operations
- ✅ **AEP - Data Ingestion** - For batch/streaming data ingestion
- ✅ **AEP - Sandbox Administration** (optional) - For sandbox management

Click **"Save configured API"**

### 5. Retrieve Credentials

After setup, navigate to **"Credentials"** > **"OAuth Server-to-Server"**:

```
Client ID: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Client Secret: [Click "Retrieve client secret"]
Organization ID: XXXXX@AdobeOrg
Technical Account ID: XXXXX@techacct.adobe.com
```

**Copy these values** - you'll need them for the CLI setup.

### 6. Configure API Scopes (Advanced)

The default scopes should include:
```
openid
AdobeID
read_organizations
additional_info.projectedProductContext
```

These are automatically included with Experience Platform API access.

### 7. Test Your Credentials

Use the built-in test tool in Developer Console:
1. Go to **"APIs & Services"** > **"OAuth Server-to-Server"**
2. Click **"Generate access token"**
3. Verify you receive a valid token

## Common Issues & Solutions

### Issue: "Invalid client credentials"
**Solution**: Double-check your Client ID and Client Secret. The secret should be retrieved fresh from the console.

### Issue: "Insufficient privileges"
**Solution**: Ensure you've selected the correct product profiles with read/write permissions.

### Issue: "Organization not found"
**Solution**: Verify the Organization ID format is `XXXXX@AdobeOrg` (not just the numeric ID).

### Issue: "Sandbox not accessible"
**Solution**: Check that your credentials have access to the specified sandbox. Default is usually `"prod"`.

## Security Best Practices

1. **Never commit credentials** to version control
   - Add `.env` to `.gitignore`
   - Use `.env.example` for templates

2. **Rotate secrets regularly**
   - Generate new Client Secret every 90 days
   - Update `.env` file accordingly

3. **Use separate credentials per environment**
   - Dev credentials for development
   - Prod credentials for production
   - Never share credentials across teams

4. **Restrict product profile access**
   - Only grant necessary permissions
   - Use principle of least privilege

## Next Steps

Once you have your credentials:

1. Run the initialization wizard:
   ```bash
   adobe-aep init
   ```

2. Test your connection:
   ```bash
   adobe-aep auth test
   ```

3. Start using the CLI:
   ```bash
   adobe-aep schema list
   ```

## Additional Resources

- [Platform API Authentication Tutorial](https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication)
- [Adobe Developer Console Documentation](https://developer.adobe.com/developer-console/docs/guides/)
- [Experience Platform API Reference](https://developer.adobe.com/experience-platform-apis/)
- [OAuth Server-to-Server Guide](https://developer.adobe.com/developer-console/docs/guides/authentication/ServerToServerAuthentication/)

## Support

If you encounter issues:
1. Check [Adobe Experience League Community](https://experienceleaguecommunities.adobe.com/t5/adobe-experience-platform/ct-p/adobe-experience-platform-community)
2. Review [AEP API Status](https://status.adobe.com/)
3. Contact Adobe Support with your Organization ID
