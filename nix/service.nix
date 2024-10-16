{config, pkgs, lib, ...}:
 let
   cfg = config.services.ipwatch;
   ipwatch = pkgs.callPackage ./python3-ipwatch.nix {};
 in

 with lib;

 {
   options = {
     services.ipwatch = {
       enable = mkOption {
         default = false;
         type = with types; bool;
         description = ''
           Start the ipwatch dashboard
         '';
       };
       email = mkOption {
         type = with types; string;
         description = ''
           Send notifications here
         '';
       };
       machine = mkOption {
         type = with types; string;
         description = ''
           Machine name
         '';
       };
       try = mkOption {
         type = with types; int;
         default = 10;
         description = ''
           Number of retries
         '';
       };
       blacklist = mkOption {
         type = with types; string;
         default = "192.168.*.*,10.*.*.*";
         description = ''
           Ignore these as external email addresses
         '';
       };
       repeat = mkOption {
         type = with types; int;
         default = 300; # every 5 min
         description = ''
           Run every N seconds
         '';
       };
     };
   };

   config = mkIf cfg.enable {
	   systemd.services.ipwatch = {
		   wantedBy = [ "multi-user.target" ];
		   after = [ "network.target" ];
		   description = "Start ipwatch IP watcher";
		   serviceConfig = {
			   ExecStart = ''${ipwatch}/bin/ipwatch --repeat ${cfg.repeat} --machine ${cfg.machine} --receiver-email ${cfg.email} --blacklist ${cfg.blacklist} --try-count ${cfg.try}'';
		   };
	   };

	   environment.systemPackages = [ ipwatch ];
   };
}
