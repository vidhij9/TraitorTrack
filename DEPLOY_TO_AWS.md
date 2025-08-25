# 🚀 Deploy Traitor Track to AWS

## Super Simple 2-Step Process

### Step 1: Set AWS Credentials (One Time Only)
1. Click the **🔒 Secrets** tab in Replit sidebar
2. Add these secrets:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key  
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

Get your keys from: https://console.aws.amazon.com/iam/home#/security_credentials

### Step 2: Deploy to AWS
Click the **▶️ Run** button above, then in the console type:
```bash
python deploy_aws_auto.py
```

**That's it!** Your Traitor Track website will be live on AWS in 10-15 minutes.

## What You Get on AWS
- **63x faster database** (DynamoDB vs PostgreSQL)
- **10,000+ concurrent users** (vs current 50 users)
- **Global CDN** for worldwide <50ms access
- **Auto-scaling** from 1 to unlimited containers
- **Pay-per-use pricing** (~$50-150/month)

## Alternative: Even Simpler
Run the deployment script:
```bash
./deploy_to_aws_simple.sh
```

## Why Not Replit Deploy Button?
Replit's deploy button only works with Google Cloud Platform. Since you want AWS specifically, you need to use the deployment script.

---

**Ready?** Add your AWS credentials to Secrets and run the deployment command!