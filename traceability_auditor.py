from metadata_store import MetadataStore

class TraceabilityAuditor:
    def __init__(self):
        self.store = MetadataStore()
    
    def generate_gap_report(self, page=1, page_size=50):
        master_rows, detected_rows = self.store.get_audit_data()
        
        # ✅ FIXED: 're q_id' → 'req_id' (critical dict key corruption - was causing KeyError)
        master_ids = {row['req_id'] for row in master_rows}
        detected_map = {}
        orphan_links = []
        
        for row in detected_rows:
            rid = row['req_id']
            if rid not in master_ids:
                orphan_links.append({
                    "req_id": rid,  # ✅ FIXED: 'req_id ' → 'req_id' (trailing space in key)
                    "found_in": row['filename'],
                    "context": row['context_snippet'][:100] + "..."
                })
            else:
                if rid not in detected_map: 
                    detected_map[rid] = []
                detected_map[rid].append(row['filename'])

        missing_reqs = []
        # ✅ FIXED: 'cover ed_reqs' → 'covered_reqs' (critical variable name corruption)
        covered_reqs = []
        
        for m_row in master_rows:
            rid = m_row['req_id']
            if rid not in detected_map:
                missing_reqs.append({
                    "req_id": rid,
                    "description": m_row['description'],
                    "status": "MISSING ❌"
                })
            else:
                covered_reqs.append({
                    "req_id": rid,
                    "found_in": list(set(detected_map[rid])),
                    "status": "COVERED ✅"
                })

        total = len(master_ids)
        score = (len(covered_reqs) / total * 100) if total > 0 else 0

        start = (page - 1) * page_size
        end = start + page_size
        
        return {
            "meta": {
                "page": page,
                "total_pages": (len(missing_reqs) + len(covered_reqs) + len(orphan_links)) // page_size + 1,
                "traceability_score": round(score, 2),
                "total_master": total
            },
            "gaps": missing_reqs[start:end],
            "orphans": orphan_links[start:end],
            "coverage": covered_reqs[start:end]
        }