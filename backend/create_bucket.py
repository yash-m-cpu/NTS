import asyncio
import sys
import aioboto3

async def main():
    session = aioboto3.Session()
    async with session.client(
        's3',
        endpoint_url='http://localhost:9000',
        aws_access_key_id='minioadmin',
        aws_secret_access_key='minioadmin',
        region_name='us-east-1'
    ) as s3:
        try:
            await s3.create_bucket(Bucket='nts-uploads')
            print("Bucket 'nts-uploads' created successfully!")
            
            # Set CORS so browser can upload directly
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag']
                }]
            }
            await s3.put_bucket_cors(Bucket='nts-uploads', CORSConfiguration=cors_configuration)
            print("CORS configuration applied successfully!")
        except Exception as e:
            if "BucketAlreadyOwnedByYou" in str(e):
                print("Bucket already exists.")
            else:
                print("ERROR:", type(e), e)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
