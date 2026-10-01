from generate_all_materials import cuts_data

total_chars = sum(len(c[5]) for c in cuts_data)
print(f"Total Cuts: {len(cuts_data)}")
print(f"Total Characters: {total_chars}")
print(f"Estimated Duration at 600 cpm: {total_chars / 600:.2f} min ({total_chars / 10:.1f} s)")
print(f"Estimated Duration at 570 cpm: {total_chars / 570:.2f} min ({total_chars / 9.5:.1f} s)")
