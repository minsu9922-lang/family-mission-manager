
    # --- Auth Methods (DB Based) ---
    def get_user_dict(self):
        """
        Populate a dictionary compatible with streamlit-authenticator from 'Users' sheet.
        Format: {'usernames': {'dad': {'name':..., 'password':..., 'email':...}, ...}}
        All timestamps are in KST (via time_utils).
        """
        users_df = self.get_data("Users")
        if users_df.empty:
            return {"usernames": {}}
        
        usernames_dict = {}
        for _, row in users_df.iterrows():
            username = row["username"]
            # Ensure fields exist
            password = row.get("password", "")
            name = row.get("name", username)
            email = row.get("email", "")
            role = row.get("role", "user")
            
            usernames_dict[username] = {
                "name": name,
                "password": password,
                "email": email,
                "role": role
            }
        
        return {"usernames": usernames_dict}

    def update_user_password(self, username, new_hash):
        """
        Updates the password hash for a specific user in 'Users' sheet.
        """
        users_df = self.get_data("Users")
        if users_df.empty:
            return False
        
        # Check if username exists
        if username in users_df["username"].values:
            idx = users_df[users_df["username"] == username].index[0]
            users_df.at[idx, "password"] = new_hash
            users_df.at[idx, "updated_at"] = time_utils.get_current_time_str() # Use KST
            
            return self.update_data("Users", users_df)
        
        return False
