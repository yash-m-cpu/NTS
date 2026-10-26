from fastapi import Depends, HTTPException

from app.api.deps import oauth2_scheme
from app.core.security import decode_access_token

ROLES = ["ADMIN", "MANAGER", "ANALYST", "RESEARCHER", "USER"]

def require_role(min_role: str):
    def role_checker(token: str = Depends(oauth2_scheme)):
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_role = payload.get("role")
        if not user_role:
            raise HTTPException(status_code=403, detail="Not enough permissions")
            
        if user_role not in ROLES:
            raise HTTPException(status_code=403, detail="Invalid role")
            
        if ROLES.index(user_role) > ROLES.index(min_role):
            raise HTTPException(status_code=403, detail="Not enough permissions")
            
        return user_role
    return role_checker
