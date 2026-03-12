from agents.database import _get_supabase

def delete_record():
    record_id = "ab7860f3-4016-48b8-81a4-4ed54d63de26"
    print(f"Attempting to delete record {record_id} from 'resumes' table...")

    try:
        client = _get_supabase()
        # Verify existence first
        res = client.table("resumes").select("id").eq("id", record_id).execute()
        if not res.data:
            print("Record not found in Supabase (maybe already deleted or wrong ID).")
        else:
            client.table("resumes").delete().eq("id", record_id).execute()
            print("Successfully deleted record from Supabase.")
    except Exception as e:
        print(f"Error deleting from Supabase: {e}")

if __name__ == "__main__":
    delete_record()
